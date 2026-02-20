"""
Agent Marketplace Manager — Publish, browse, install, rate, and review agents across tenants.
Provides a shared catalog where agents can be published by one tenant and installed by others.
In-memory store with structured models for marketplace listings.
"""

import uuid
import copy
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ListingStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    FEATURED = "featured"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class ListingCategory(str, Enum):
    PROCUREMENT = "procurement"
    DATA_ANALYTICS = "data"
    CUSTOMER_SUPPORT = "support"
    AUTOMATION = "automation"
    FINANCE = "finance"
    HR = "hr"
    LEGAL = "legal"
    IT_OPS = "it_ops"
    CUSTOM = "custom"


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: f"rev-{uuid.uuid4().hex[:8]}")
    user_id: str
    user_name: str = ""
    tenant_id: str = ""
    rating: int = 5  # 1-5
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InstallRecord(BaseModel):
    install_id: str = Field(default_factory=lambda: f"inst-{uuid.uuid4().hex[:8]}")
    listing_id: str
    installed_by: str = ""
    tenant_id: str = ""
    agent_id: str = ""  # the new agent_id created from the install
    installed_at: datetime = Field(default_factory=datetime.utcnow)


class MarketplaceListing(BaseModel):
    """A published agent available in the marketplace."""
    listing_id: str = Field(default_factory=lambda: f"mkt-{uuid.uuid4().hex[:8]}")
    # Source agent info
    source_agent_id: str
    source_tenant_id: str = ""
    publisher_id: str = ""
    publisher_name: str = ""

    # Display info
    name: str
    description: str = ""
    long_description: str = ""
    category: str = "custom"
    tags: List[str] = Field(default_factory=list)
    icon: str = ""  # icon identifier
    complexity: str = "intermediate"  # basic, intermediate, advanced
    version: str = "1.0.0"

    # Agent config snapshot (serialized at publish time)
    agent_snapshot: Dict[str, Any] = Field(default_factory=dict)

    # Marketplace metadata
    status: ListingStatus = ListingStatus.DRAFT
    featured: bool = False
    install_count: int = 0
    avg_rating: float = 0.0
    review_count: int = 0
    reviews: List[Review] = Field(default_factory=list)
    installs: List[InstallRecord] = Field(default_factory=list)

    # Capabilities summary (for display)
    tools_used: List[str] = Field(default_factory=list)
    model_id: str = ""
    rag_enabled: bool = False
    requires_api_keys: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None


class MarketplaceManager:
    """
    Manages the agent marketplace catalog.
    Agents can be published from any tenant and installed by others.
    """

    def __init__(self):
        self._listings: Dict[str, MarketplaceListing] = {}

    # ── Publish ─────────────────────────────────────────────────────

    def publish(
        self,
        agent_definition,  # AgentDefinition from agent_registry
        publisher_id: str = "",
        publisher_name: str = "",
        tenant_id: str = "",
        category: str = "custom",
        long_description: str = "",
        tags: Optional[List[str]] = None,
        icon: str = "",
        complexity: str = "intermediate",
        requires_api_keys: Optional[List[str]] = None,
    ) -> MarketplaceListing:
        """Publish an agent to the marketplace."""
        # Snapshot the agent config
        snapshot = agent_definition.model_dump(mode="json", by_alias=True)
        # Remove sensitive fields
        for key in ("access_control", "endpoint"):
            snapshot.pop(key, None)

        listing = MarketplaceListing(
            source_agent_id=agent_definition.agent_id,
            source_tenant_id=tenant_id,
            publisher_id=publisher_id,
            publisher_name=publisher_name,
            name=agent_definition.name,
            description=agent_definition.description,
            long_description=long_description or agent_definition.description,
            category=category,
            tags=tags or agent_definition.tags,
            icon=icon,
            complexity=complexity,
            agent_snapshot=snapshot,
            status=ListingStatus.PUBLISHED,
            tools_used=[t.tool_name for t in agent_definition.tools] if agent_definition.tools else [],
            model_id=agent_definition.model_config_.model_id if hasattr(agent_definition, 'model_config_') else "",
            rag_enabled=agent_definition.rag_config.enabled if hasattr(agent_definition, 'rag_config') else False,
            requires_api_keys=requires_api_keys or [],
            published_at=datetime.utcnow(),
        )

        self._listings[listing.listing_id] = listing
        logger.info(f"Published agent '{listing.name}' to marketplace as {listing.listing_id}")
        return listing

    # ── Browse ──────────────────────────────────────────────────────

    def list_published(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "popular",  # popular, newest, rating, name
        limit: int = 50,
        offset: int = 0,
    ) -> List[MarketplaceListing]:
        """Browse published marketplace listings."""
        listings = [
            l for l in self._listings.values()
            if l.status in (ListingStatus.PUBLISHED, ListingStatus.FEATURED)
        ]

        if category and category != "all":
            listings = [l for l in listings if l.category == category]

        if search:
            q = search.lower()
            listings = [
                l for l in listings
                if q in l.name.lower()
                or q in l.description.lower()
                or any(q in t.lower() for t in l.tags)
            ]

        # Sort
        if sort_by == "popular":
            listings.sort(key=lambda l: l.install_count, reverse=True)
        elif sort_by == "newest":
            listings.sort(key=lambda l: l.published_at or l.created_at, reverse=True)
        elif sort_by == "rating":
            listings.sort(key=lambda l: l.avg_rating, reverse=True)
        elif sort_by == "name":
            listings.sort(key=lambda l: l.name.lower())

        return listings[offset:offset + limit]

    def get(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def get_by_publisher(self, publisher_id: str) -> List[MarketplaceListing]:
        return [l for l in self._listings.values() if l.publisher_id == publisher_id]

    def get_featured(self) -> List[MarketplaceListing]:
        return [l for l in self._listings.values() if l.status == ListingStatus.FEATURED]

    # ── Install (clone agent to a new tenant) ───────────────────────

    def install(
        self,
        listing_id: str,
        agent_registry,  # AgentRegistry instance
        installed_by: str = "",
        tenant_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Install a marketplace agent into the caller's tenant.
        Creates a clone of the agent from the listing snapshot.
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return None

        snapshot = listing.agent_snapshot
        if not snapshot:
            return None

        # Import here to avoid circular
        from backend.agent_service.agent_registry import (
            AgentDefinition, AgentStatus, ModelConfig, RAGConfig,
            MemoryConfig, DBConfig, AccessControl,
        )

        # Build new agent from snapshot
        new_agent_id = f"agt-{uuid.uuid4().hex[:8]}"
        mc_data = snapshot.get("model_config") or snapshot.get("model_config_") or {}
        rag_data = snapshot.get("rag_config") or {}
        mem_data = snapshot.get("memory_config") or {}

        agent = AgentDefinition(
            agent_id=new_agent_id,
            name=f"{listing.name}",
            description=listing.description,
            tags=listing.tags + ["marketplace", f"from:{listing.listing_id}"],
            context=snapshot.get("context", ""),
            status=AgentStatus.DRAFT,
            access_control=AccessControl(owner_id=installed_by),
            metadata={
                "marketplace_listing_id": listing.listing_id,
                "marketplace_installed_at": datetime.utcnow().isoformat(),
                "marketplace_publisher": listing.publisher_name,
                "marketplace_version": listing.version,
            },
        )
        # Set model config
        if mc_data:
            agent.model_config_ = ModelConfig(**{
                k: v for k, v in mc_data.items()
                if k in ModelConfig.model_fields
            })
        if rag_data:
            agent.rag_config = RAGConfig(**{
                k: v for k, v in rag_data.items()
                if k in RAGConfig.model_fields
            })
        if mem_data:
            agent.memory_config = MemoryConfig(**{
                k: v for k, v in mem_data.items()
                if k in MemoryConfig.model_fields
            })

        # Restore tools from snapshot
        tools_data = snapshot.get("tools", [])
        from backend.agent_service.agent_registry import ToolBinding
        agent.tools = []
        for t in tools_data:
            if isinstance(t, dict):
                agent.tools.append(ToolBinding(**{
                    k: v for k, v in t.items()
                    if k in ToolBinding.model_fields
                }))

        # Register via agent_registry (sync create for simplicity)
        created = agent_registry.create(agent)

        # Track install
        record = InstallRecord(
            listing_id=listing_id,
            installed_by=installed_by,
            tenant_id=tenant_id,
            agent_id=created.agent_id,
        )
        listing.installs.append(record)
        listing.install_count += 1
        listing.updated_at = datetime.utcnow()

        logger.info(f"Installed marketplace listing {listing_id} as agent {created.agent_id}")

        return {
            "agent_id": created.agent_id,
            "name": created.name,
            "listing_id": listing_id,
            "listing_name": listing.name,
            "install_id": record.install_id,
        }

    # ── Rate & Review ───────────────────────────────────────────────

    def add_review(
        self,
        listing_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
        user_name: str = "",
        tenant_id: str = "",
    ) -> Optional[Review]:
        listing = self._listings.get(listing_id)
        if not listing:
            return None

        rating = max(1, min(5, rating))
        review = Review(
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            rating=rating,
            comment=comment,
        )
        listing.reviews.append(review)
        listing.review_count = len(listing.reviews)
        listing.avg_rating = round(
            sum(r.rating for r in listing.reviews) / len(listing.reviews), 1
        )
        listing.updated_at = datetime.utcnow()
        return review

    def get_reviews(self, listing_id: str) -> List[Review]:
        listing = self._listings.get(listing_id)
        if not listing:
            return []
        return sorted(listing.reviews, key=lambda r: r.created_at, reverse=True)

    # ── Management ──────────────────────────────────────────────────

    def update_listing(self, listing_id: str, updates: Dict[str, Any]) -> Optional[MarketplaceListing]:
        listing = self._listings.get(listing_id)
        if not listing:
            return None
        for k, v in updates.items():
            if hasattr(listing, k) and k not in ("listing_id", "created_at", "installs", "reviews"):
                setattr(listing, k, v)
        listing.updated_at = datetime.utcnow()
        return listing

    def unpublish(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.DEPRECATED
        listing.updated_at = datetime.utcnow()
        return True

    def set_featured(self, listing_id: str, featured: bool = True) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.featured = featured
        listing.status = ListingStatus.FEATURED if featured else ListingStatus.PUBLISHED
        listing.updated_at = datetime.utcnow()
        return True

    def delete(self, listing_id: str) -> bool:
        return self._listings.pop(listing_id, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        listings = list(self._listings.values())
        published = [l for l in listings if l.status in (ListingStatus.PUBLISHED, ListingStatus.FEATURED)]
        return {
            "total_listings": len(listings),
            "published": len(published),
            "featured": sum(1 for l in listings if l.status == ListingStatus.FEATURED),
            "total_installs": sum(l.install_count for l in listings),
            "total_reviews": sum(l.review_count for l in listings),
            "categories": list(set(l.category for l in published)),
        }

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get categories with listing counts."""
        published = [
            l for l in self._listings.values()
            if l.status in (ListingStatus.PUBLISHED, ListingStatus.FEATURED)
        ]
        cat_counts: Dict[str, int] = {}
        for l in published:
            cat_counts[l.category] = cat_counts.get(l.category, 0) + 1
        return [
            {"id": cat, "count": count}
            for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])
        ]
