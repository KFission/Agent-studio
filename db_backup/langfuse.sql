--
-- PostgreSQL database dump
--

\restrict 4ubirsawhg1gqnrDlgbZEmBalhzPq1I6YAFxKAvF5LuCoKKzMIOXFmwho4kwCyO

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: AnnotationQueueObjectType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."AnnotationQueueObjectType" AS ENUM (
    'TRACE',
    'OBSERVATION'
);


--
-- Name: AnnotationQueueStatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."AnnotationQueueStatus" AS ENUM (
    'PENDING',
    'COMPLETED'
);


--
-- Name: CommentObjectType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."CommentObjectType" AS ENUM (
    'TRACE',
    'OBSERVATION',
    'SESSION',
    'PROMPT'
);


--
-- Name: DatasetStatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."DatasetStatus" AS ENUM (
    'ACTIVE',
    'ARCHIVED'
);


--
-- Name: JobConfigState; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."JobConfigState" AS ENUM (
    'ACTIVE',
    'INACTIVE'
);


--
-- Name: JobExecutionStatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."JobExecutionStatus" AS ENUM (
    'COMPLETED',
    'ERROR',
    'PENDING',
    'CANCELLED'
);


--
-- Name: JobType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."JobType" AS ENUM (
    'EVAL'
);


--
-- Name: ObservationLevel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."ObservationLevel" AS ENUM (
    'DEBUG',
    'DEFAULT',
    'WARNING',
    'ERROR'
);


--
-- Name: ObservationType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."ObservationType" AS ENUM (
    'SPAN',
    'EVENT',
    'GENERATION'
);


--
-- Name: Role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."Role" AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER',
    'VIEWER',
    'NONE'
);


--
-- Name: ScoreDataType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."ScoreDataType" AS ENUM (
    'CATEGORICAL',
    'NUMERIC',
    'BOOLEAN'
);


--
-- Name: ScoreSource; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."ScoreSource" AS ENUM (
    'ANNOTATION',
    'API',
    'EVAL'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: Account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."Account" (
    id text NOT NULL,
    type text NOT NULL,
    provider text NOT NULL,
    "providerAccountId" text NOT NULL,
    refresh_token text,
    access_token text,
    expires_at integer,
    token_type text,
    scope text,
    id_token text,
    session_state text,
    user_id text NOT NULL,
    expires_in integer,
    ext_expires_in integer,
    refresh_token_expires_in integer,
    created_at integer
);


--
-- Name: Session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."Session" (
    id text NOT NULL,
    expires timestamp(3) without time zone NOT NULL,
    session_token text NOT NULL,
    user_id text NOT NULL
);


--
-- Name: _prisma_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public._prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL
);


--
-- Name: annotation_queue_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.annotation_queue_items (
    id text NOT NULL,
    queue_id text NOT NULL,
    object_id text NOT NULL,
    object_type public."AnnotationQueueObjectType" NOT NULL,
    status public."AnnotationQueueStatus" DEFAULT 'PENDING'::public."AnnotationQueueStatus" NOT NULL,
    locked_at timestamp(3) without time zone,
    locked_by_user_id text,
    annotator_user_id text,
    completed_at timestamp(3) without time zone,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: annotation_queues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.annotation_queues (
    id text NOT NULL,
    name text NOT NULL,
    description text,
    score_config_ids text[] DEFAULT ARRAY[]::text[],
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    note text,
    public_key text NOT NULL,
    hashed_secret_key text NOT NULL,
    display_secret_key text NOT NULL,
    last_used_at timestamp(3) without time zone,
    expires_at timestamp(3) without time zone,
    project_id text NOT NULL,
    fast_hashed_secret_key text
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id text NOT NULL,
    project_id text,
    resource_type text NOT NULL,
    resource_id text NOT NULL,
    action text NOT NULL,
    before text,
    after text,
    org_id text NOT NULL,
    user_org_role text NOT NULL,
    user_project_role text
);


--
-- Name: background_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.background_migrations (
    id text NOT NULL,
    name text NOT NULL,
    script text NOT NULL,
    args jsonb NOT NULL,
    finished_at timestamp(3) without time zone,
    failed_at timestamp(3) without time zone,
    failed_reason text,
    worker_id text,
    locked_at timestamp(3) without time zone,
    state jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: batch_exports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch_exports (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    user_id text NOT NULL,
    finished_at timestamp(3) without time zone,
    expires_at timestamp(3) without time zone,
    name text NOT NULL,
    status text NOT NULL,
    query jsonb NOT NULL,
    format text NOT NULL,
    url text,
    log text
);


--
-- Name: comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comments (
    id text NOT NULL,
    project_id text NOT NULL,
    object_type public."CommentObjectType" NOT NULL,
    object_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    content text NOT NULL,
    author_user_id text
);


--
-- Name: cron_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cron_jobs (
    name text NOT NULL,
    last_run timestamp(3) without time zone,
    state text,
    job_started_at timestamp(3) without time zone
);


--
-- Name: dataset_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_items (
    id text NOT NULL,
    input jsonb,
    expected_output jsonb,
    source_observation_id text,
    dataset_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status public."DatasetStatus" DEFAULT 'ACTIVE'::public."DatasetStatus" NOT NULL,
    source_trace_id text,
    metadata jsonb,
    project_id text NOT NULL
);


--
-- Name: dataset_run_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_run_items (
    id text NOT NULL,
    dataset_run_id text NOT NULL,
    dataset_item_id text NOT NULL,
    observation_id text,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    trace_id text NOT NULL,
    project_id text NOT NULL
);


--
-- Name: dataset_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_runs (
    id text NOT NULL,
    name text NOT NULL,
    dataset_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata jsonb,
    description text,
    project_id text NOT NULL
);


--
-- Name: datasets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.datasets (
    id text NOT NULL,
    name text NOT NULL,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    description text,
    metadata jsonb
);


--
-- Name: eval_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_templates (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    name text NOT NULL,
    version integer NOT NULL,
    prompt text NOT NULL,
    model text NOT NULL,
    model_params jsonb NOT NULL,
    vars text[] DEFAULT ARRAY[]::text[],
    output_schema jsonb NOT NULL,
    provider text NOT NULL
);


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    data jsonb NOT NULL,
    url text,
    method text,
    headers jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: job_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_configurations (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    job_type public."JobType" NOT NULL,
    eval_template_id text,
    score_name text NOT NULL,
    filter jsonb NOT NULL,
    target_object text NOT NULL,
    variable_mapping jsonb NOT NULL,
    sampling numeric(65,30) NOT NULL,
    delay integer NOT NULL,
    status public."JobConfigState" DEFAULT 'ACTIVE'::public."JobConfigState" NOT NULL
);


--
-- Name: job_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_executions (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    job_configuration_id text NOT NULL,
    status public."JobExecutionStatus" NOT NULL,
    start_time timestamp(3) without time zone,
    end_time timestamp(3) without time zone,
    error text,
    job_input_trace_id text,
    job_output_score_id text,
    job_input_dataset_item_id text,
    job_input_observation_id text
);


--
-- Name: llm_api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_api_keys (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    provider text NOT NULL,
    display_secret_key text NOT NULL,
    secret_key text NOT NULL,
    project_id text NOT NULL,
    base_url text,
    adapter text NOT NULL,
    custom_models text[] DEFAULT '{}'::text[] NOT NULL,
    with_default_models boolean DEFAULT true NOT NULL,
    config jsonb
);


--
-- Name: media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media (
    id text NOT NULL,
    sha_256_hash character(44) NOT NULL,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    uploaded_at timestamp(3) without time zone,
    upload_http_status integer,
    upload_http_error text,
    bucket_path text NOT NULL,
    bucket_name text NOT NULL,
    content_type text NOT NULL,
    content_length bigint NOT NULL
);


--
-- Name: membership_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.membership_invitations (
    id text NOT NULL,
    email text NOT NULL,
    project_id text,
    invited_by_user_id text,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    org_id text NOT NULL,
    org_role public."Role" NOT NULL,
    project_role public."Role"
);


--
-- Name: models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.models (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text,
    model_name text NOT NULL,
    match_pattern text NOT NULL,
    start_date timestamp(3) without time zone,
    input_price numeric(65,30),
    output_price numeric(65,30),
    total_price numeric(65,30),
    unit text,
    tokenizer_config jsonb,
    tokenizer_id text
);


--
-- Name: observation_media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.observation_media (
    id text NOT NULL,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    media_id text NOT NULL,
    trace_id text NOT NULL,
    observation_id text NOT NULL,
    field text NOT NULL
);


--
-- Name: observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.observations (
    id text NOT NULL,
    name text,
    start_time timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time timestamp(3) without time zone,
    parent_observation_id text,
    type public."ObservationType" NOT NULL,
    trace_id text,
    metadata jsonb,
    model text,
    "modelParameters" jsonb,
    input jsonb,
    output jsonb,
    level public."ObservationLevel" DEFAULT 'DEFAULT'::public."ObservationLevel" NOT NULL,
    status_message text,
    completion_start_time timestamp(3) without time zone,
    completion_tokens integer DEFAULT 0 NOT NULL,
    prompt_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    version text,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    unit text,
    prompt_id text,
    input_cost numeric(65,30),
    output_cost numeric(65,30),
    total_cost numeric(65,30),
    internal_model text,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    calculated_input_cost numeric(65,30),
    calculated_output_cost numeric(65,30),
    calculated_total_cost numeric(65,30),
    internal_model_id text
);


--
-- Name: prompts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prompts (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    created_by text NOT NULL,
    name text NOT NULL,
    version integer NOT NULL,
    is_active boolean,
    config json DEFAULT '{}'::json NOT NULL,
    prompt jsonb NOT NULL,
    type text DEFAULT 'text'::text NOT NULL,
    tags text[] DEFAULT ARRAY[]::text[],
    labels text[] DEFAULT ARRAY[]::text[]
);


--
-- Name: observations_view; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.observations_view AS
 SELECT o.id,
    o.name,
    o.start_time,
    o.end_time,
    o.parent_observation_id,
    o.type,
    o.trace_id,
    o.metadata,
    o.model,
    o."modelParameters",
    o.input,
    o.output,
    o.level,
    o.status_message,
    o.completion_start_time,
    o.completion_tokens,
    o.prompt_tokens,
    o.total_tokens,
    o.version,
    o.project_id,
    o.created_at,
    o.updated_at,
    o.unit,
    o.prompt_id,
    p.name AS prompt_name,
    p.version AS prompt_version,
    o.input_cost,
    o.output_cost,
    o.total_cost,
    o.internal_model,
    m.id AS model_id,
    m.start_date AS model_start_date,
    m.input_price,
    m.output_price,
    m.total_price,
    m.tokenizer_config,
        CASE
            WHEN ((o.calculated_input_cost IS NULL) AND (o.input_cost IS NULL) AND (o.output_cost IS NULL) AND (o.total_cost IS NULL)) THEN ((o.prompt_tokens)::numeric * m.input_price)
            ELSE COALESCE(o.calculated_input_cost, o.input_cost)
        END AS calculated_input_cost,
        CASE
            WHEN ((o.calculated_output_cost IS NULL) AND (o.input_cost IS NULL) AND (o.output_cost IS NULL) AND (o.total_cost IS NULL)) THEN ((o.completion_tokens)::numeric * m.output_price)
            ELSE COALESCE(o.calculated_output_cost, o.output_cost)
        END AS calculated_output_cost,
        CASE
            WHEN ((o.calculated_total_cost IS NULL) AND (o.input_cost IS NULL) AND (o.output_cost IS NULL) AND (o.total_cost IS NULL)) THEN
            CASE
                WHEN ((m.total_price IS NOT NULL) AND (o.total_tokens IS NOT NULL)) THEN (m.total_price * (o.total_tokens)::numeric)
                ELSE (((o.prompt_tokens)::numeric * m.input_price) + ((o.completion_tokens)::numeric * m.output_price))
            END
            ELSE COALESCE(o.calculated_total_cost, o.total_cost)
        END AS calculated_total_cost,
        CASE
            WHEN (o.end_time IS NULL) THEN NULL::double precision
            ELSE ((EXTRACT(epoch FROM o.end_time) - EXTRACT(epoch FROM o.start_time)))::double precision
        END AS latency,
        CASE
            WHEN ((o.completion_start_time IS NOT NULL) AND (o.start_time IS NOT NULL)) THEN (EXTRACT(epoch FROM (o.completion_start_time - o.start_time)))::double precision
            ELSE NULL::double precision
        END AS time_to_first_token
   FROM ((public.observations o
     LEFT JOIN LATERAL ( SELECT models.id,
            models.created_at,
            models.updated_at,
            models.project_id,
            models.model_name,
            models.match_pattern,
            models.start_date,
            models.input_price,
            models.output_price,
            models.total_price,
            models.unit,
            models.tokenizer_config,
            models.tokenizer_id
           FROM public.models
          WHERE (((models.project_id = o.project_id) OR (models.project_id IS NULL)) AND (models.model_name = o.internal_model) AND ((models.start_date < o.start_time) OR (models.start_date IS NULL)) AND (o.unit = models.unit))
          ORDER BY models.project_id, models.start_date DESC NULLS LAST
         LIMIT 1) m ON (true))
     LEFT JOIN LATERAL ( SELECT prompts.id,
            prompts.created_at,
            prompts.updated_at,
            prompts.project_id,
            prompts.created_by,
            prompts.name,
            prompts.version,
            prompts.is_active,
            prompts.config,
            prompts.prompt,
            prompts.type,
            prompts.tags,
            prompts.labels
           FROM public.prompts
          WHERE ((prompts.id = o.prompt_id) AND (prompts.project_id = o.project_id))
         LIMIT 1) p ON (true));


--
-- Name: organization_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_memberships (
    id text NOT NULL,
    org_id text NOT NULL,
    user_id text NOT NULL,
    role public."Role" NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id text NOT NULL,
    name text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    cloud_config jsonb
);


--
-- Name: posthog_integrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.posthog_integrations (
    project_id text NOT NULL,
    encrypted_posthog_api_key text NOT NULL,
    posthog_host_name text NOT NULL,
    last_sync_at timestamp(3) without time zone,
    enabled boolean NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: prices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prices (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    model_id text NOT NULL,
    usage_type text NOT NULL,
    price numeric(65,30) NOT NULL
);


--
-- Name: project_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_memberships (
    project_id text NOT NULL,
    user_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    org_membership_id text NOT NULL,
    role public."Role" NOT NULL
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name text NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    org_id text NOT NULL
);


--
-- Name: score_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.score_configs (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    name text NOT NULL,
    data_type public."ScoreDataType" NOT NULL,
    is_archived boolean DEFAULT false NOT NULL,
    min_value double precision,
    max_value double precision,
    categories jsonb,
    description text
);


--
-- Name: scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scores (
    id text NOT NULL,
    "timestamp" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name text NOT NULL,
    value double precision,
    observation_id text,
    trace_id text NOT NULL,
    comment text,
    source public."ScoreSource" NOT NULL,
    project_id text NOT NULL,
    author_user_id text,
    config_id text,
    data_type public."ScoreDataType" DEFAULT 'NUMERIC'::public."ScoreDataType" NOT NULL,
    string_value text,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    queue_id text
);


--
-- Name: sso_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sso_configs (
    domain text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    auth_provider text NOT NULL,
    auth_config jsonb
);


--
-- Name: trace_media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trace_media (
    id text NOT NULL,
    project_id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    media_id text NOT NULL,
    trace_id text NOT NULL,
    field text NOT NULL
);


--
-- Name: trace_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trace_sessions (
    id text NOT NULL,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    project_id text NOT NULL,
    bookmarked boolean DEFAULT false NOT NULL,
    public boolean DEFAULT false NOT NULL
);


--
-- Name: traces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.traces (
    id text NOT NULL,
    "timestamp" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name text,
    project_id text NOT NULL,
    metadata jsonb,
    external_id text,
    user_id text,
    release text,
    version text,
    public boolean DEFAULT false NOT NULL,
    bookmarked boolean DEFAULT false NOT NULL,
    input jsonb,
    output jsonb,
    session_id text,
    tags text[] DEFAULT ARRAY[]::text[],
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: traces_view; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.traces_view AS
 WITH observations_metrics AS (
         SELECT o_1.trace_id,
            o_1.project_id,
            ((EXTRACT(epoch FROM COALESCE(max(o_1.end_time), max(o_1.start_time))))::double precision - (EXTRACT(epoch FROM min(o_1.start_time)))::double precision) AS duration
           FROM public.observations o_1
          GROUP BY o_1.project_id, o_1.trace_id
        )
 SELECT t.id,
    t."timestamp",
    t.name,
    t.project_id,
    t.metadata,
    t.external_id,
    t.user_id,
    t.release,
    t.version,
    t.public,
    t.bookmarked,
    t.input,
    t.output,
    t.session_id,
    t.tags,
    t.created_at,
    t.updated_at,
    o.duration
   FROM (public.traces t
     LEFT JOIN observations_metrics o ON (((t.id = o.trace_id) AND (t.project_id = o.project_id))));


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id text NOT NULL,
    name text,
    email text,
    email_verified timestamp(3) without time zone,
    password text,
    image text,
    created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    feature_flags text[] DEFAULT ARRAY[]::text[],
    admin boolean DEFAULT false NOT NULL
);


--
-- Name: verification_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verification_tokens (
    identifier text NOT NULL,
    token text NOT NULL,
    expires timestamp(3) without time zone NOT NULL
);


--
-- Data for Name: Account; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."Account" (id, type, provider, "providerAccountId", refresh_token, access_token, expires_at, token_type, scope, id_token, session_state, user_id, expires_in, ext_expires_in, refresh_token_expires_in, created_at) FROM stdin;
\.


--
-- Data for Name: Session; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."Session" (id, expires, session_token, user_id) FROM stdin;
\.


--
-- Data for Name: _prisma_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public._prisma_migrations (id, checksum, finished_at, migration_name, logs, rolled_back_at, started_at, applied_steps_count) FROM stdin;
a08676d6-b785-4df7-9663-0743b82f1cd6	c418394abc6167c883f1456639e995ab5054a8257e8dba37b7a95c76ba59af0c	2026-02-16 23:24:14.176169+00	20230710200816_scores_add_comment	\N	\N	2026-02-16 23:24:14.175686+00	1
f664cdeb-540d-4e01-982c-651baa2e7ba4	45fc679b7dbbe0f2954623bfe4e29932374cdc3167f8395728ef5c20115e5665	2026-02-16 23:24:14.13832+00	20230518191501_init	\N	\N	2026-02-16 23:24:14.133514+00	1
07e307a4-ab9f-40a2-b360-d8c827bce231	6462cebefe054956e2fa9948435590bd4dae0d58f75cf2ecba57059f2c0909f8	2026-02-16 23:24:14.168235+00	20230623172401_observation_add_level_and_status_message	\N	\N	2026-02-16 23:24:14.167499+00	1
930cca46-4a0b-496e-94a9-feaa822ad121	b9c79e332b90d28b1711534e53622f297a6a888aa7d6c1c1832185d1fef2c929	2026-02-16 23:24:14.140655+00	20230518193415_add_observaionts_and_traces	\N	\N	2026-02-16 23:24:14.138635+00	1
ab00c515-3c5a-4cfc-87aa-2f9a97954f4f	2f2fd22c3cc8bd21f6f23c88b7d5ef34674431520d0e55a37f8239e4a58afebd	2026-02-16 23:24:14.142844+00	20230518193521_changes	\N	\N	2026-02-16 23:24:14.141426+00	1
3d01ea93-2f6d-40a0-9e98-00dc601aa92d	d2c9bf829418360a44d1022156aaa8e95df92c940b5dfe962f8a7f7260cb5520	2026-02-16 23:24:14.145117+00	20230522092340_add_metrics_and_observation_types	\N	\N	2026-02-16 23:24:14.143145+00	1
6df7e466-8fcd-43c2-92c2-a3cd2bd3d849	2480f771a6b4dea1f541c0b231784e5cebf2c443ac7636da6a411c4914f1cbd4	2026-02-16 23:24:14.1693+00	20230626095337_external_trace_id	\N	\N	2026-02-16 23:24:14.168561+00	1
9ab3a6ac-35b3-4c3c-8367-0311e02990a7	28c59a2bd9b846d914083efdc1b51eb96a1db66af370b3dddd5040a57ec9088b	2026-02-16 23:24:14.14615+00	20230522094431_endtime_optional	\N	\N	2026-02-16 23:24:14.145592+00	1
4f6c4a0f-29c7-4bdc-a170-e2afca01c12e	755b1309b9c12e892f5a5f6db4e14f15b2d77ab61f76baab4c3621ea5e94fa6c	2026-02-16 23:24:14.147185+00	20230522131516_default_timestamp	\N	\N	2026-02-16 23:24:14.146326+00	1
11100db7-2a84-4b41-8582-08dda985f7fc	7f995c9ff2b7e3f70bb5eeebb2108552feaf5f8a51154727c36db9466f0e3ec4	2026-02-16 23:24:14.186523+00	20230731162154_score_value_float	\N	\N	2026-02-16 23:24:14.184683+00	1
e97cf667-e1e7-4162-babd-0a42c6885fe2	66607eae9ccdfb92f30d859bcff0838e5df64c76da43ffbb25a65845dc63234e	2026-02-16 23:24:14.150598+00	20230523082455_rename_metrics_to_gradings	\N	\N	2026-02-16 23:24:14.147808+00	1
eabf7b3a-5112-422f-9cf4-a49412298f5b	e5b55a82f4be9d623abac6ef0d9d00da2bf437f60454ed46bb1defa30e388692	2026-02-16 23:24:14.170512+00	20230705160335_add_created_updated_timestamps	\N	\N	2026-02-16 23:24:14.169668+00	1
4e0451b4-3b07-40c7-9d03-7e34df773054	ff4107185d8f98b9d850e571a464bb806dade0f482984b3e29c019cb4d51397c	2026-02-16 23:24:14.153147+00	20230523084523_rename_to_score	\N	\N	2026-02-16 23:24:14.150825+00	1
309bef5b-2ddb-4eaf-835e-b7e2f6eea082	ab80a534dfa4779eeae4ae5aeac192eea19b283671d6083c8f112e3c8a4229df	2026-02-16 23:24:14.153864+00	20230529140133_user_add_pw	\N	\N	2026-02-16 23:24:14.15332+00	1
638e4862-4726-4052-9eb0-144c166e13dd	f7c8e195215bf8a82ff89093a94aef748c209361aa05a48273f2084c49f05cd6	2026-02-16 23:24:14.1773+00	20230711104810_traces_add_index	\N	\N	2026-02-16 23:24:14.176539+00	1
c5e82f57-5323-46a0-aefb-13359584d746	f0ef0a5663ceecf04816edea38d3fe93cf07f4c8031d2b7e185ec2e5fe39f0fa	2026-02-16 23:24:14.163109+00	20230530204241_auth_api_ui	\N	\N	2026-02-16 23:24:14.154296+00	1
800f0bd5-9ee5-4561-a1f1-120ea53f625d	83f6a1d39c744faecc145e812f8ecca54267ac363f6315aa8afc3d890bf1f02d	2026-02-16 23:24:14.171155+00	20230706195819_add_completion_start_time	\N	\N	2026-02-16 23:24:14.170671+00	1
95b6aefc-5476-40bc-b4f2-b34149cde3a9	5e2e9d168251bab10d33e5f65a848c48d5f4ab762427ddd0f81e907c3339eb9a	2026-02-16 23:24:14.16416+00	20230618125818_remove_status_from_trace	\N	\N	2026-02-16 23:24:14.163497+00	1
4e3e1945-88f3-48e7-8c0e-94583e8733b2	a7808d643321e4bf3d0628b256abb7d088e964c48698af6fdd7f32969dfd41aa	2026-02-16 23:24:14.166356+00	20230620181114_restructure	\N	\N	2026-02-16 23:24:14.164332+00	1
1ab90baa-3627-4d82-bc74-87dacab54b9b	025c499c8b6f13676087e2e419671177a85a3ebad3a53cf84c7f70b0cfe01efe	2026-02-16 23:24:14.167287+00	20230622114254_new_oservations	\N	\N	2026-02-16 23:24:14.166549+00	1
a1da1f1c-4b3d-4280-b0df-05568d65ada0	ffbe75ad538d26b0864f8b8915115e0fbdd56fbc93a4d3a634d53488b741d403	2026-02-16 23:24:14.171949+00	20230707132314_traces_project_id_index	\N	\N	2026-02-16 23:24:14.171335+00	1
7c8f8f68-f427-468c-ba1c-5f698d8918fe	4cd20328eb9aa4ce2f0fe7dab5e00c412215e2c4423902d79cdebd7b0e2325f0	2026-02-16 23:24:14.182533+00	20230720164603_migrate_tokens	\N	\N	2026-02-16 23:24:14.181881+00	1
edfb78c7-7135-4a09-bad1-36e9bd50a9ed	362123c958d4fd06df3c816b74b4336ad2373f1505be12c84046e1364dd9dc10	2026-02-16 23:24:14.172969+00	20230707133415_user_add_email_index	\N	\N	2026-02-16 23:24:14.172271+00	1
864eab9a-76e4-460c-919a-d9b87dff8370	5755c1c8449e6a74016e9e7e42acc446746a3c41f21e07c317a66417fd399d94	2026-02-16 23:24:14.17805+00	20230711110517_memberships_add_userid_index	\N	\N	2026-02-16 23:24:14.177473+00	1
29539c30-4422-4641-8d1b-0b638b9afa24	e7de5bcadea82b38002ead42a8e99f532e5fe2c178ba53d5954ef2c60a0115b3	2026-02-16 23:24:14.174421+00	20230710105741_added_indices	\N	\N	2026-02-16 23:24:14.173141+00	1
91467102-a4aa-468c-b5f9-039cc20a78b5	18a5a7ffe2b0ec8c008a1336826e3e07525f42a27e981f0a778533947b09e92d	2026-02-16 23:24:14.175476+00	20230710114928_traces_add_user_id	\N	\N	2026-02-16 23:24:14.17461+00	1
cdaf0a18-8021-4806-aa90-c3715a9eb411	225ccf9170a395e34586c954db9c71b84f4300a07ef67e5ff116d2d08f80f37f	2026-02-16 23:24:14.179716+00	20230711112235_fix_indices	\N	\N	2026-02-16 23:24:14.178218+00	1
d8e342b2-03f8-4abd-9f47-4886fecb884c	9994a7038fc3ba73d3b5e833ded5825ec58505918d6b4eca646dbfca60a899b8	2026-02-16 23:24:14.183533+00	20230720172051_tokens_non_null	\N	\N	2026-02-16 23:24:14.182754+00	1
ebccbaf0-5c63-4841-bd28-6ad16ae38b1b	502d73e77f606982c12150e119f9214a7d8116d3d4d947ea37130d6aaf9280cd	2026-02-16 23:24:14.180587+00	20230717190411_users_feature_flags	\N	\N	2026-02-16 23:24:14.179991+00	1
899c050d-06c4-4628-b1a9-775eef9f93a3	9d3edea83f7e43616f70059fd0dbe6236133ac5fcd9883ac59b298e97fcd2e68	2026-02-16 23:24:14.181671+00	20230720162550_tokens	\N	\N	2026-02-16 23:24:14.180952+00	1
a871f59b-ef5e-4e52-8f30-92953fe67ca8	7c025190192fb785a7f3728ebab61bb167f3be07233341678c640bd31360fce5	2026-02-16 23:24:14.191245+00	20230810191452_traceid_nullable_on_observations	\N	\N	2026-02-16 23:24:14.190651+00	1
42debe44-3059-4bd1-9b80-170d94b4f169	882b8cd48edf35b50633d13833aa0c8b92f70b707c3fc035fe0e59d2355a3a95	2026-02-16 23:24:14.184344+00	20230721111651_drop_usage_json	\N	\N	2026-02-16 23:24:14.183757+00	1
277ef169-659a-491e-8990-b4a3a85aed13	056d2e25ef8ebb7b2b7eee99a708ab8feffa348896301c8a1a67524e3c2fddf8	2026-02-16 23:24:14.190233+00	20230809132331_add_project_id_to_observations	\N	\N	2026-02-16 23:24:14.189039+00	1
74498c75-fc9b-43c2-b07a-0d06141e5988	05604cd4b32a7e41e21a314c7e78fd1b5883a9582acb5f4308ee7053af9707d7	2026-02-16 23:24:14.18746+00	20230803093326_add_release_and_version	\N	\N	2026-02-16 23:24:14.186754+00	1
d1d3728b-6ccc-4e86-adbb-e17adc9bece7	ef6d52cd7eae4e95cf21b942289d9efb69e7f60eb5d3ca281d252c54e2b77ede	2026-02-16 23:24:14.188808+00	20230809093636_remove_foreign_keys	\N	\N	2026-02-16 23:24:14.187674+00	1
7bdb87c8-d3df-4c24-b35d-7743d6224dfd	f409d263846f578bba696959b5ebfaa60a9534a407c6ad8c8fc32604ab7adfd1	2026-02-16 23:24:14.192002+00	20230810191453_project_id_not_null	\N	\N	2026-02-16 23:24:14.191465+00	1
c0bf4674-21b3-4f2f-a875-5fce30dec152	f998a3d872a1056949638870ce35fedb364d37297a784ecbcd1f95faf04a4c5c	2026-02-16 23:24:14.192745+00	20230814184705_add_viewer_membership_role	\N	\N	2026-02-16 23:24:14.192219+00	1
a260006c-ac53-4286-bac6-85020b532c74	51ccaa1ee0828dcb0cf731b019486c2f39c5b1bdd09046ab90f9ba6ec13be1af	2026-02-16 23:24:14.194216+00	20230901155252_add_pricings_table	\N	\N	2026-02-16 23:24:14.192996+00	1
71f5faba-ff13-448d-8720-e8b53dc5cc67	5b8a5e3d5880fa10be8005ca6e4d682104dae3f816e162c3db94c41753a8e1c5	2026-02-16 23:24:14.195338+00	20230901155336_add_pricing_data	\N	\N	2026-02-16 23:24:14.194585+00	1
9dade622-e763-4e41-9cc2-aadfcd3aacbf	e31a4c1059dcbabbdc2ab6aecb50328bef42e809ed206485aba37c437c5cebc2	2026-02-16 23:24:14.196458+00	20230907204921_add_cron_jobs_table	\N	\N	2026-02-16 23:24:14.195531+00	1
3a68617e-eb03-4478-8e1b-3dfb64963f20	800d6b5782b4564cfa092fd57f42ec2283537d439f167419211669aaa7df3ee2	2026-02-16 23:24:14.229202+00	20231119171940_bookmarked	\N	\N	2026-02-16 23:24:14.227959+00	1
a6792294-9dd8-497b-bbf1-194c3a7f39b7	285bbb0b1c1ad7b8ee2d29ae7477b3f5b1b0e53fc58e9d75a287aaac715d498b	2026-02-16 23:24:14.197585+00	20230907225603_projects_updated_at	\N	\N	2026-02-16 23:24:14.196684+00	1
8a46f725-ef08-4a51-84b3-fd9481ba2950	578777f46933e33a0dc8e7c78f054c86dd0ed1413f67dc2d6334365cfda4c6bb	2026-02-16 23:24:14.216828+00	20231018130032_add_per_1000_chars_pricing	\N	\N	2026-02-16 23:24:14.216399+00	1
a9fa05c2-996f-4580-b563-645cacb8cb2f	d11aeff0b05af374c3306cdb12cc18afb7f73c5b8ce2c50757745ce5775340e2	2026-02-16 23:24:14.198593+00	20230907225604_api_keys_publishable_to_public	\N	\N	2026-02-16 23:24:14.197798+00	1
e3faeb19-9780-4aa8-869d-d056ff23f952	378a5dd5ba691270826895506d53e8a6acc4ebba29f8226dfa0d78e698040c5e	2026-02-16 23:24:14.199553+00	20230910164603_cron_add_state	\N	\N	2026-02-16 23:24:14.199+00	1
80282eb2-58a6-4021-9f92-581a81805d60	00cea39de0d75e817cfadcd95f852d4a84e00c1f67930d518ae4d452c93ac177	2026-02-16 23:24:14.224562+00	20231110012457_observation_created_at	\N	\N	2026-02-16 23:24:14.224044+00	1
a9c5c862-ec68-408e-8b50-760f47feb863	d4af17aef307dba854b4b896df6f998cef8ac211fb792b7e90c7fe6fa4a9e4c3	2026-02-16 23:24:14.200342+00	20230912115644_add_trace_public_bool	\N	\N	2026-02-16 23:24:14.199741+00	1
fb992aa2-b8cc-421b-aa00-02db1330c9da	c087cf267a4c8b52ec4cebf0612b840d2136475e4776e9206778830256ce3f32	2026-02-16 23:24:14.218215+00	20231019094815_add_additional_secret_key_column	\N	\N	2026-02-16 23:24:14.217042+00	1
77aa1efc-29a1-455d-8f86-8a0eefa58d43	2026ed8d4e73d7d09741dbedf1fe73233e624f3e7f81b2a2b9243f415168ebb2	2026-02-16 23:24:14.201681+00	20230918180320_add_indices	\N	\N	2026-02-16 23:24:14.200591+00	1
2de66528-8629-481f-9c5b-bde8ef671046	6bfdc95391ba091dc9d96899dbe7f967814cf42eb6388b664d9d76d8982add70	2026-02-16 23:24:14.20262+00	20230922030325_add_observation_index	\N	\N	2026-02-16 23:24:14.201951+00	1
ebed9c6f-8d90-483d-8fdf-d1f68e686d37	ea9794f2d79f49b88ab95b90335fe97cd7ccc3d7f1dd156259a5e5aa1c107043	2026-02-16 23:24:14.207503+00	20230924232619_datasets_init	\N	\N	2026-02-16 23:24:14.203032+00	1
83457463-e66d-4806-be7b-445c24265c36	44810e0e19455ef071bec618d10951ba956e7a112631eb3f4c313fe903db7267	2026-02-16 23:24:14.219019+00	20231021182825_user_emails_all_lowercase	\N	\N	2026-02-16 23:24:14.218382+00	1
654796eb-ea57-48aa-b7f8-e17e3e97831c	6db5841932092efa895afe4c027079a9c48ae252181c8e0c3985c6d08f96ba8a	2026-02-16 23:24:14.209013+00	20230924232620_datasets_continued	\N	\N	2026-02-16 23:24:14.207691+00	1
cd720bf8-711c-4e9c-a562-62ee1db8da3d	e8f8302423f78da25f0349a5da4083160f574c98ccc2b3e28f91d16cfa1ad499	2026-02-16 23:24:14.209798+00	20231004005909_add_parent_observation_id_index	\N	\N	2026-02-16 23:24:14.209232+00	1
80711314-1830-4ec9-bd1b-5e48f06abd93	8f1b13112f4627c886c705d33920578b19fea917471b7367191300eebef544fc	2026-02-16 23:24:14.210553+00	20231005064433_add_release_index	\N	\N	2026-02-16 23:24:14.209968+00	1
d76cfc29-2244-4b69-94c1-b13db28c2f23	6456651794d1f7215c7f39238725764948ce71b7df386639d2d4f58da2e93335	2026-02-16 23:24:14.21977+00	20231025153548_add_headers_to_events	\N	\N	2026-02-16 23:24:14.219212+00	1
fc03bea0-286d-4ce3-b022-5996eda09d17	dfeb488d9be2f37c669211d8fee91cc67d384eee1532512a00328195fd259e27	2026-02-16 23:24:14.214117+00	20231009095917_add_ondelete_cascade	\N	\N	2026-02-16 23:24:14.21091+00	1
479987eb-9b21-4fd9-ac1d-e64b67e1fa74	e08e3d28e1b13a6df4f7eb43bd81d427f86792a9235dfa123db11b67343c1d82	2026-02-16 23:24:14.215498+00	20231012161041_add_events_table	\N	\N	2026-02-16 23:24:14.214293+00	1
e24d15ff-8133-4573-8926-ff53b0dd6b1e	1074f270d9b48baa51d22c0c90218cdc47dc3338a5f0ea90bd72ef5ea5e2cf88	2026-02-16 23:24:14.225316+00	20231110012829_observation_created_at_index	\N	\N	2026-02-16 23:24:14.224757+00	1
b75dabf7-b084-4064-b205-d442b87d7fb9	52d73a2c8f5927da07492f83ffc94ce4a3cdc93232be0291d0faf77bc5ba8eed	2026-02-16 23:24:14.216233+00	20231014131841_users_add_admin_flag	\N	\N	2026-02-16 23:24:14.215691+00	1
6ca29ae6-35ed-48cd-bffa-5046e891160e	cc2235e89e6815af4002bd4aa6941e16dd452efe9dc5d59ac0c390589160a7ac	2026-02-16 23:24:14.220662+00	20231030184329_events_add_index_on_projectid	\N	\N	2026-02-16 23:24:14.220041+00	1
d2ff9b41-ac8b-476f-966e-7cabb902d852	f5ef1377c36e5301cf312bb60c6bb647bdb3de2db1d847003b4cfd3e24ca9ccc	2026-02-16 23:24:14.221623+00	20231104004529_scores_add_index	\N	\N	2026-02-16 23:24:14.220887+00	1
1fc5b891-5789-4b4d-a85e-8cfe7e809566	9f5a355bf0c6c5fa36b37c898b338a234d43efa01d387eca439a95d674721ca2	2026-02-16 23:24:14.238529+00	20231230151856_add_prompt_table	\N	\N	2026-02-16 23:24:14.236654+00	1
dd80f132-4adc-4451-8e09-f1240fd0a5d3	2f634dc6a7e272e3715472968da531e23c9dda562d5d137e6bfe7195d51761ab	2026-02-16 23:24:14.223178+00	20231104005403_fkey_indicies	\N	\N	2026-02-16 23:24:14.22179+00	1
9aa73cd6-7d7f-488d-8a05-11dfd3b161d2	3920714d62de04345531777f14fe9a02b8982890c93f0b57512c0ab55755ee79	2026-02-16 23:24:14.226019+00	20231112095703_observations_add_unique_constraint	\N	\N	2026-02-16 23:24:14.225482+00	1
cb5f3aa9-a772-44db-8a66-a28a9dadc638	85bf236e16abc39747ea773383c06cd06208e2d147237beb0b20b48318397e7e	2026-02-16 23:24:14.223872+00	20231106213824_add_openai_models	\N	\N	2026-02-16 23:24:14.223392+00	1
6d6f42ea-f225-4c5a-972e-945051dea6a7	0be96056b9709a8b7899d555e228d5c0098f1e6b358c6e016bb3843b7846b3f6	2026-02-16 23:24:14.231286+00	20231129013314_invites	\N	\N	2026-02-16 23:24:14.229435+00	1
93915545-cdf1-42ce-96fd-755377da093d	5881fcf2e0d44375b52e6228413774f3154ab9fab3492f8ff24a24c2f044033b	2026-02-16 23:24:14.226974+00	20231116005353_scores_unique_id_projectid	\N	\N	2026-02-16 23:24:14.226218+00	1
006c92a4-75c7-4aae-b263-7ca7254211a4	8fee27ef5b07ba63a31cf88aee365f6f9c66b8cb5a08492b7f19c2a1eef249e4	2026-02-16 23:24:14.227641+00	20231119171939_cron_add_job_started_at	\N	\N	2026-02-16 23:24:14.22719+00	1
a0f9fb65-3e0a-4da2-8a5b-3199f3abb148	1b774d2ddbe9ae0f7cf8b60beaef0d27a6f5e8b09840e342ffd85c63c5de517d	2026-02-16 23:24:14.235746+00	20231223230007_cloud_config	\N	\N	2026-02-16 23:24:14.235195+00	1
3591d85c-4fa6-48ae-b310-faf1ae74da53	401f5230ee1dccb765509321e8075652e71ae4ec28f5648a6b2ee151fc58d90b	2026-02-16 23:24:14.234051+00	20231130003317_trace_session_input_output	\N	\N	2026-02-16 23:24:14.231526+00	1
0fe894c7-87cd-4228-a069-02bab1d73f8d	f73f71a1a394677fb4ddd00cfe2238c40190f875525473d9ebf80f15fc89a2e7	2026-02-16 23:24:14.23496+00	20231204223505_add_unit_to_observations	\N	\N	2026-02-16 23:24:14.234309+00	1
272df32d-a5fa-4c82-a9bc-3c5920218cec	14911fffc711830a28304af98b2c9fe31f5f78fb568281090a75f4f7958ba942	2026-02-16 23:24:14.236451+00	20231223230008_accounts_add_cols_azure_ad_auth	\N	\N	2026-02-16 23:24:14.235957+00	1
2d758f2c-4a09-41f0-b6ed-46cbac3ce467	9f7ef155730980f10cf9c84fdcce91b80822a8ff1d7d35720b544f851397a0e5	2026-02-16 23:24:14.240261+00	20240104210051_add_model_indices	\N	\N	2026-02-16 23:24:14.23954+00	1
55554079-e398-439a-b7e3-6e32a6f9b16a	7919b5dfcacec288b646f23c83f6adbf5f69eba50d2de4a35eb2b9d3029e4729	2026-02-16 23:24:14.239334+00	20240103135918_add_pricings	\N	\N	2026-02-16 23:24:14.238712+00	1
706531f5-85ad-4aa4-b1a6-f01b29a2b8ba	ed03d628f2755b0b16963a8d20b72440588a7ed57a4f1652d9b128e5dcfbf1b3	2026-02-16 23:24:14.241281+00	20240104210052_add_model_indices_pricing	\N	\N	2026-02-16 23:24:14.240453+00	1
439a3c07-f582-4d44-a935-8bb95852b227	08918b17989f2bd0e36f80c5255042f807afe428186c68cf334fa01953153807	2026-02-16 23:24:14.242183+00	20240105010215_add_tags_in_traces	\N	\N	2026-02-16 23:24:14.241479+00	1
4af0419b-dab1-4928-9fce-ed7a5ea4085d	18fba86141a537df2fdf6bc8b8d8cd1abcdef25ca0dca43d1983fb23dac4db72	2026-02-16 23:24:14.243315+00	20240105170551_index_tags_in_traces	\N	\N	2026-02-16 23:24:14.242341+00	1
e1898dcf-9d6a-4d26-a532-29641eda76e2	de4c1bc9e76dc2ad02e5cedc68bc20450c80307c64123469b925b1ba1787449c	2026-02-16 23:24:14.244215+00	20240106195340_drop_dataset_status	\N	\N	2026-02-16 23:24:14.243655+00	1
c8a8d3c5-cb3d-49be-b208-19121480bd32	795187b23b16aceb796a10b5a43327cd3f767a0048f7ae8cb4d209695e49f18d	2026-02-16 23:24:14.266867+00	20240215234937_fix_observations_view	\N	\N	2026-02-16 23:24:14.265454+00	1
d02a54a8-443f-438e-9cca-b9952bb5491a	9d7148c925f6643b17c1aad933fce92bdcbc8fa2304eb97be11c0aa32747664a	2026-02-16 23:24:14.245121+00	20240111152124_add_gpt_35_pricing	\N	\N	2026-02-16 23:24:14.244599+00	1
9499a8f2-48ea-4671-8389-bfb9d3d40171	fcbff614561f2c09501be18aad566624e04bf390aef8c072596ac2b793d10cb7	2026-02-16 23:24:14.258283+00	20240130100110_usage_unit_nullable	\N	\N	2026-02-16 23:24:14.257686+00	1
a0328a25-06fa-4d59-a7dd-d8de4d2194fc	9496ee3af1202cb3f9d6f0d4bb88c521e0e796a04bc8e02622718a63ba79b710	2026-02-16 23:24:14.245811+00	20240117151938_traces_remove_unique_id_external	\N	\N	2026-02-16 23:24:14.245331+00	1
ca8eae02-3b58-4c3f-801c-dce296ca44e0	c5919ee7870f36a7555024eb2256b3a28c8d978032dcd943047e5cff27a86cba	2026-02-16 23:24:14.246468+00	20240117165747_add_cost_to_observations	\N	\N	2026-02-16 23:24:14.24597+00	1
0236ea33-c740-4801-80df-bdea3460ae29	ad8869aea6b98159c54bd3f2fcfb4ee1114ba54a7bf5726378dc2edd6f8077eb	2026-02-16 23:24:14.248105+00	20240118204639_add_models_table	\N	\N	2026-02-16 23:24:14.246795+00	1
2a481a52-0c96-4256-94c7-391d15c349c9	c301dfa0db4367a4691bf520cb0c0b377b10e2ef4ca66f39f818284b23d0cfa2	2026-02-16 23:24:14.259009+00	20240130160110_claude_models	\N	\N	2026-02-16 23:24:14.258468+00	1
6c97b9dc-67a2-4f7b-a182-e204f4e277b7	7211b935cb3f52c11c7ebd0ac540bbbd01bb2010e51ad412d2956645c02724b7	2026-02-16 23:24:14.24872+00	20240118204936_add_internal_model	\N	\N	2026-02-16 23:24:14.24827+00	1
672b5993-233a-4752-b33f-51a504ce6d94	b79f2ca2011baa6604eec15e549996af3a10e396b706aff73b6ca36c08291d99	2026-02-16 23:24:14.250562+00	20240118204937_add_observations_view	\N	\N	2026-02-16 23:24:14.249088+00	1
b6a48c00-7220-4319-8931-6f4748915cd5	2ab605d386e52af31b6328f5542d63ec6a6b19db9bda8f2e4888a7de7154b2ae	2026-02-16 23:24:14.281044+00	20240304123642_traces_view_improvement	\N	\N	2026-02-16 23:24:14.279898+00	1
e1c79da7-cbab-4050-8d64-50097e10a318	2c075714bdce7df89f328062021733fd62880ff7cdb91a1d0a7aab2659a89d06	2026-02-16 23:24:14.251506+00	20240118235424_add_index_to_models	\N	\N	2026-02-16 23:24:14.250746+00	1
13cdccd2-7fde-4b1a-85a5-70d84beea4f0	af31e8b4be701e97ccf87d4692055d2cc7ece9d74cc424e05dfb2775de5a7efe	2026-02-16 23:24:14.259801+00	20240131184148_add_finetuned_and_vertex_models	\N	\N	2026-02-16 23:24:14.25921+00	1
1bc715f4-44aa-45c9-97ae-8317ca2a8590	c76d5a31377660ce77e890a918ffa07bd2db8c8c94b04753befbc27d152492ea	2026-02-16 23:24:14.252187+00	20240119140941_add_tokenizer_id	\N	\N	2026-02-16 23:24:14.251673+00	1
e2a0cc80-fcfc-433c-8886-6b268e7d2ad4	08f7d11bd5deec873669ca10101dd0a05669bb04eb300ef0ee7b6d3517ae0c24	2026-02-16 23:24:14.252823+00	20240119164147_make_model_params_nullable	\N	\N	2026-02-16 23:24:14.252351+00	1
c9cff5cc-cc4e-479c-b50d-a329d623c9c4	540712b04f0fbaf449eaf229210e04dec83280878842c7c3d9956e4ff98334ce	2026-02-16 23:24:14.267723+00	20240219162415_add_prompt_config	\N	\N	2026-02-16 23:24:14.267065+00	1
22fb84c9-c3b4-45ec-b1d1-6c4f16d33234	3b0d3c46459cc2770d6e8d9db6fc139f859792da5b89937114dd09b17dac0dd4	2026-02-16 23:24:14.254077+00	20240119164148_add_models	\N	\N	2026-02-16 23:24:14.253246+00	1
00967eb8-15c2-4980-b224-97fe7d0138ce	3bc4965e82cd4645da383ef6f6582a7efd7f5bf27e912af1efe18ff62e014db1	2026-02-16 23:24:14.260464+00	20240203184148_update_pricing	\N	\N	2026-02-16 23:24:14.260021+00	1
ad5931fa-a8f7-4449-8012-5fc3eda0dfb9	73f7212daa54130c6fa91fc17d840262ec948b11aafce49ea3e8ce7d4f3cbef1	2026-02-16 23:24:14.255891+00	20240124140443_session_composite_key	\N	\N	2026-02-16 23:24:14.254243+00	1
a129a1df-01c7-480c-961b-bfd8b6c23de5	4ec1ad8229c185a7afaa62357879a60d4f59b35a103975030ce43d67823096c9	2026-02-16 23:24:14.256666+00	20240124164148_correct_models	\N	\N	2026-02-16 23:24:14.256087+00	1
47a1af8a-5b8b-4720-a413-ec480f9eb29d	546c704d2869f4d382fb591fd20b14c489e99fffaa5655c45a3a86e7a7d488c5	2026-02-16 23:24:14.257359+00	20240126184148_new_models copy	\N	\N	2026-02-16 23:24:14.256869+00	1
a8d70d4d-6847-471e-83f8-d229c56fea3b	3e0cc893b4ec41ef43740af577aef359e2c742c338c8fc5421f766d75cce1292	2026-02-16 23:24:14.262745+00	20240212175433_add_audit_log_table	\N	\N	2026-02-16 23:24:14.260967+00	1
bdb841fa-216c-4b5d-bed7-8ec57655d828	f2af6a57ddd2aab8adeaa5a3c6571cd8ab8538b071fb01e07c35d277203ae6b8	2026-02-16 23:24:14.272862+00	20240226202041_add_observations_trace_id_project_id_type_start_time_idx	\N	\N	2026-02-16 23:24:14.272041+00	1
487f529a-d8db-4196-8828-6c510edbc5a2	4a1b6917569327219e620f0cca78446c360958d5a91226b7f60bd4626ffb38d0	2026-02-16 23:24:14.263415+00	20240213124148_update_openai_pricing	\N	\N	2026-02-16 23:24:14.262941+00	1
2677ee33-6f9f-4b60-a08b-e269f1bf65ce	909cae9daaf399b3ab6e9c03142fa4b80d7b09f44165944b9a09007d829d6f28	2026-02-16 23:24:14.268709+00	20240226165118_add_observations_index	\N	\N	2026-02-16 23:24:14.267904+00	1
23d2dbd4-9d8b-4fcd-a1b8-5aa368466303	a942356a983650fb3aa2974690956869324993c3a546ea83d3ae26d2a98db7c1	2026-02-16 23:24:14.264315+00	20240214232619_prompts_add_indicies	\N	\N	2026-02-16 23:24:14.263579+00	1
c8cc0e79-4fb4-4ee5-95b9-52d642621e50	00a42d4d8bd4090cf94d90eeb82fe803d23d802dcdb6c058b2371a75d951519a	2026-02-16 23:24:14.265106+00	20240215224148_update_openai_pricing	\N	\N	2026-02-16 23:24:14.264658+00	1
413940c2-8818-4c86-8950-5c5fd3d6a9e2	d498837088f8de279f4c04655af668c34f3febd961c95390a0441cb0ee0a3db6	2026-02-16 23:24:14.277024+00	20240228103642_observations_view_cte	\N	\N	2026-02-16 23:24:14.275706+00	1
158d2311-b662-49ea-a651-bb2d0a334165	58e1bb0a84cb20a36c750b9d13c1371e44cd1a4947d5bdb37754a23d664c5e33	2026-02-16 23:24:14.269864+00	20240226182815_add_model_index	\N	\N	2026-02-16 23:24:14.269074+00	1
02e67fb1-374b-458c-abd9-1bbe1b8d9059	e31ee1ec510ded08a1813273056149bfe345651ce02d9ab31883dde10e390afe	2026-02-16 23:24:14.274515+00	20240226203642_rewrite_observations_view	\N	\N	2026-02-16 23:24:14.273244+00	1
e979df46-d5aa-489d-8d47-12b098ca44f0	2cb0786da90de9c0a6e2983075362c76163e0635f9d347da0686b9c0434b8f0f	2026-02-16 23:24:14.270936+00	20240226183642_add_observations_index	\N	\N	2026-02-16 23:24:14.270202+00	1
6986a680-6981-4385-b13e-f315d9e3ca7c	e733981599148cbb086a4eb4e7276fac2059ce3b60b3acf1443c3ec648f1d233	2026-02-16 23:24:14.27184+00	20240226202040_add_observations_trace_id_project_id_start_time_idx	\N	\N	2026-02-16 23:24:14.271101+00	1
bec092bc-9974-4a1a-b527-24ec839c05e7	5603e17abf74b6c9e4191ff261e56e63641a90c5e04d99c5f04be174d1a90d76	2026-02-16 23:24:14.275506+00	20240227112101_index_prompt_id_in_observations	\N	\N	2026-02-16 23:24:14.274842+00	1
415be743-0a23-4882-83b1-dff659212368	83902ab9281b0b9b7257768518cbfb6895d382f30e6594b2058507d173bfa519	2026-02-16 23:24:14.279579+00	20240304123642_traces_view	\N	\N	2026-02-16 23:24:14.278718+00	1
4dc9ccb7-fe18-4544-bf72-c6da1b1a4279	96e0223ba9bb5ec06dc4c53988451298d6cf9df6b83da89262280ceb3c203d59	2026-02-16 23:24:14.278384+00	20240228123642_observations_view_fix	\N	\N	2026-02-16 23:24:14.277207+00	1
5e1c15d8-37e0-4328-809d-29fb487bfa27	b9abacb6b7858085eff8230a9950eaffe2e557c67981592097a2b93204b3c5ec	2026-02-16 23:24:14.281927+00	20240304222519_scores_add_index	\N	\N	2026-02-16 23:24:14.281249+00	1
7b32c1ac-58c0-474c-b9e3-810449414db5	f8e14cfb18416f04c49e67c2e9c97675b1d01a1a60a549d784cfbcd52f308771	2026-02-16 23:24:14.282816+00	20240305095119_add_observations_index	\N	\N	2026-02-16 23:24:14.282094+00	1
f161fb45-6965-4d28-a0c0-4066aa7d2dae	498c50087ca98fffe98b041b77c8ef195888e35e607b3c0d64643d9275e83935	2026-02-16 23:24:14.283835+00	20240305100713_traces_add_index	\N	\N	2026-02-16 23:24:14.283151+00	1
45f168f0-ef81-4176-b25a-50ff86619ddc	89a9d0e9dd25662dd684333947df23ea4165a4adec9995e281b33fecdd60b775	2026-02-16 23:24:14.284804+00	20240307090110_claude_model_three	\N	\N	2026-02-16 23:24:14.284288+00	1
16d9fe54-6668-4e0a-97e1-371e68a49ded	7a8d3f1cb3ce402ca6de3b8af2f9f402770d7bb1b9a0ba740dd691b5e88feb1f	2026-02-16 23:24:14.285564+00	20240307185543_score_add_source_nullable	\N	\N	2026-02-16 23:24:14.284969+00	1
b3c8fc03-003d-44e0-8280-8829f2647451	cbf36bf3115f7c66934d46e7d8f4a21c7465f9d00569d619b7382028ee422eb3	2026-02-16 23:24:14.297734+00	20240404210315_dataset_add_descriptions	\N	\N	2026-02-16 23:24:14.297198+00	1
18c6b7dc-329b-4d88-bf95-43547c002840	b9c551f91d345926b3c740563aecff3904717185b84dcdf74c0b2521ffa2cb63	2026-02-16 23:24:14.286816+00	20240307185544_score_add_name_index	\N	\N	2026-02-16 23:24:14.285924+00	1
8975cdf1-553e-4962-be64-91b6aec6e591	0cec970448bd9ff3a78acdcce5519f9c2154378ccc3a3acbd79266478f66238e	2026-02-16 23:24:14.28782+00	20240307185725_backfill_score_source	\N	\N	2026-02-16 23:24:14.28717+00	1
959fc9b1-c2ae-4820-816b-27880ffdd488	c8ea9587bcf109835eb4b8cb882e121c35624d5e9f90e21886de3b7ee5793312	2026-02-16 23:24:14.320395+00	20240424150909_add_job_execution_index	\N	\N	2026-02-16 23:24:14.319668+00	1
48bd66c2-9941-447b-887e-01c6bcc9d001	1a476db15f8f2a6becbde3c804623832542a9d2dc1233389e9b4d1c9047a5b43	2026-02-16 23:24:14.288468+00	20240312195727_score_source_drop_default	\N	\N	2026-02-16 23:24:14.288008+00	1
edc07ba8-4095-4fa3-ad2e-b21d90a03960	b5d68c44ed85196b038921cde3faf6241050b76781a9d93981346165436c6ed7	2026-02-16 23:24:14.298749+00	20240404232317_dataset_items_backfill_source_trace_id	\N	\N	2026-02-16 23:24:14.298257+00	1
4b642c70-1d30-48e2-96b1-3e66f3209a5d	137f83659a950bdc6497c2030f61bd070264ee14387f3e11143f55ae2c3d810e	2026-02-16 23:24:14.289031+00	20240314090110_claude_model	\N	\N	2026-02-16 23:24:14.288638+00	1
07f5113c-f9ed-4f12-8bbc-4f3cebf48699	9e7f1d6a2d8e12037a931e8d8c86e552366e8056d2a9adb847f84da5c6972398	2026-02-16 23:24:14.290395+00	20240325211959_remove_example_table	\N	\N	2026-02-16 23:24:14.289491+00	1
a2bb32d3-aae5-48f3-9513-ee10b4500e4f	e0d84647251c69f99883c12c21eb9cbad9f0fc1059b58cce3296edeebdc1b8dc	2026-02-16 23:24:14.310662+00	20240414203636_ee_add_sso_configs	\N	\N	2026-02-16 23:24:14.309665+00	1
3ab244bf-527e-4f02-9f94-7d5fdf7f503f	48d049e8d66ed3f4b0336d857ae4bfeb7f39dd9ee1070fbe4bede32630478e7b	2026-02-16 23:24:14.291142+00	20240325212245_dataset_runs_add_metadata	\N	\N	2026-02-16 23:24:14.290713+00	1
f4ae05c0-1395-43b8-9e04-8308cb009bd5	82c21f5f2399c1173c734d8a157b4b0dac6821cbbc36dce8ba058caf40681ff7	2026-02-16 23:24:14.29999+00	20240405124810_prompt_to_json	\N	\N	2026-02-16 23:24:14.299077+00	1
a0892416-78ed-4036-82e0-9889141fb7be	3fa446eb946ec9e8f56c4665e02aea106727c4058acd89dd758900273a2183d8	2026-02-16 23:24:14.292309+00	20240326114211_dataset_run_item_bind_to_trace	\N	\N	2026-02-16 23:24:14.291315+00	1
70a31863-c89a-4fbf-9a99-51b0ad29e3e8	f6efc777385ff3f04b4c93745d7a66fe953a4fb4544203ad22808b80468f3578	2026-02-16 23:24:14.293167+00	20240326114337_dataset_run_item_backfill_trace_id	\N	\N	2026-02-16 23:24:14.292476+00	1
516a081a-3736-478e-a19c-cc9995981dfd	7c084b86913a91f9b8658084f6b8f6526bce2d0de4842c8f68e07f30f1f46fe9	2026-02-16 23:24:14.293958+00	20240326115136_dataset_run_item_traceid_non_null	\N	\N	2026-02-16 23:24:14.293507+00	1
3df7ff61-72ce-4a63-b62f-182e4b6186e4	206607c9c910399b23bb8217092e4b17fd428f2890efb49f1ad65dceaa55f3d1	2026-02-16 23:24:14.305181+00	20240408133037_add_objects_for_evals	\N	\N	2026-02-16 23:24:14.300182+00	1
87208981-1f57-4bcf-88b2-9bae7cc97339	afe59690f207d0f4481d9a54af3e743622a88a68ad46d4eb2597c2b7a953fc66	2026-02-16 23:24:14.295+00	20240326115424_dataset_run_item_index_trace	\N	\N	2026-02-16 23:24:14.294297+00	1
2dc19bec-f22a-4445-8a96-3abdc37e303b	10e5a3983b46239bbb0b6ad8617901df3c7eaa53df0b879577528d7e14d84d91	2026-02-16 23:24:14.295685+00	20240328065738_dataset_item_input_nullable	\N	\N	2026-02-16 23:24:14.295168+00	1
566dd69f-a6db-4dc4-a425-75b5a0585caf	b01064942f09a3e944a7db83a680ba04e135b6aee91569445ba295a2ce443f74	2026-02-16 23:24:14.316364+00	20240420134232_posthog_integration_created_at	\N	\N	2026-02-16 23:24:14.315835+00	1
e77ab64f-850a-4673-badc-bd2ed6770ac9	04c22689adda42b47ce94563fc3e834507c8b214a20ae1d379b2cfa9ed4e6d73	2026-02-16 23:24:14.296679+00	20240404203640_dataset_item_source_trace_id	\N	\N	2026-02-16 23:24:14.295872+00	1
b4882e09-ed1b-4670-954d-9082e12d700d	dcd8dcb804ab5eeb3cc813b88ea510578a6b481e5756628b0fa7d061d9aa79a5	2026-02-16 23:24:14.31157+00	20240415235737_index_models_model_name	\N	\N	2026-02-16 23:24:14.310835+00	1
eeff2264-0ca4-4a5c-a08e-fc0852b8b8c0	b9711c48f8a9d20c8705c31f1a2bd4a4e1e3473e7de6f884ced0776773dea897	2026-02-16 23:24:14.306126+00	20240408134328_prompt_table_add_tags	\N	\N	2026-02-16 23:24:14.305528+00	1
23e721ba-f027-461b-8b3e-d9e91c87a3b3	017eaef133c6ad53c86e655daf6ef310f5e8870d197b32b91b22feea8589c20d	2026-02-16 23:24:14.307102+00	20240408134330_prompt_table_add_index_to_tags	\N	\N	2026-02-16 23:24:14.306442+00	1
9adf710e-2c4c-4d33-bd74-bca97d92f783	5b74cc3719cc73c4a9561521df9593a0b72b7f71a7edc6fc962259855d1b4597	2026-02-16 23:24:14.307943+00	20240411134330_model_updates	\N	\N	2026-02-16 23:24:14.307468+00	1
3a0e33f7-e507-4bf0-aa25-2111a240b1b1	20f9110c61428813f2d32bff079f64fe35ee3dbb6eb40241c24885ca87e44226	2026-02-16 23:24:14.312624+00	20240416173813_add_internal_model_index	\N	\N	2026-02-16 23:24:14.311941+00	1
285d2e5c-55af-4e11-aa59-51c65b19430d	86412f0fd3a38ecf7aba62d2df6bc63f21d8545c6846e7ad450f1ba1054ec0ef	2026-02-16 23:24:14.308742+00	20240411194142_update_job_config_status	\N	\N	2026-02-16 23:24:14.308098+00	1
08d2112b-425c-4bf7-a152-41f431070c7a	0f44dce07307ae9364e93449837fe6fc6189780dd94b7d506f8c2f653423b42a	2026-02-16 23:24:14.309335+00	20240411224142_update_models	\N	\N	2026-02-16 23:24:14.30892+00	1
33a0761f-ad02-45b3-9627-4e5653e384cb	e79db3e95ce362750535a772337f79cd94bc37890e58ce3c05aa0253afe1d1d6	2026-02-16 23:24:14.313913+00	20240417102742_metadata_on_dataset_and_dataset_item	\N	\N	2026-02-16 23:24:14.313024+00	1
1a098177-03dc-4c2b-ad09-6688734d61ed	b5153e69a337304509d94116fc42eac4ae838617041d473e361627e99d78eaeb	2026-02-16 23:24:14.317138+00	20240423174013_update_models	\N	\N	2026-02-16 23:24:14.316528+00	1
bf4dc0ba-f3cd-40ab-9cbe-139e6b8ead76	d53f2ddcfda91be76c40f87c0ebdeee510cf7316e6ce8578e16a3a068daf0bd5	2026-02-16 23:24:14.315665+00	20240419152924_posthog_integration_settings	\N	\N	2026-02-16 23:24:14.314304+00	1
cef87d11-7795-4cef-a008-e2a9957df6e5	a15e5ed199ff9e77ad2ab1920262094a07c63c5bf639929e7912e3ec5b6f1da0	2026-02-16 23:24:14.324612+00	20240503130335_traces_index_created_at	\N	\N	2026-02-16 23:24:14.323774+00	1
761de7ab-580b-4f54-8531-7236b12f379c	0a6f2078af2b92a1d61d36449f3646fb8adda99acb6ee214451b8c2a7a62c36c	2026-02-16 23:24:14.319326+00	20240423192655_add_llm_api_keys	\N	\N	2026-02-16 23:24:14.317505+00	1
8729d974-75f4-4eff-aaf0-5dbcdb49f7ea	6c5083ecdb222c9a4566fac6a4364a349351e868bb68eff17a7c8c48bacf39c1	2026-02-16 23:24:14.323166+00	20240503125742_traces_add_createdat_updatedat	\N	\N	2026-02-16 23:24:14.322483+00	1
95917c30-e416-4efd-ac9e-f840f4bfc633	a2ff78bbd0982e80edcc312bb686a9d33f4bde7e675d0915ba570aff2931307d	2026-02-16 23:24:14.321309+00	20240429124411_add_prompt_version_labels	\N	\N	2026-02-16 23:24:14.320576+00	1
dac92c03-9489-4358-9869-b216b144c5f4	caf1f29f946abe2c7774657473a274866a1bab1a4d4b368bac32154c263aba22	2026-02-16 23:24:14.321978+00	20240429194411_add_latest_prompt_tag	\N	\N	2026-02-16 23:24:14.321482+00	1
b818933e-aae6-47a8-bc09-92e8ef5d362c	6d3ba16762dc0033c95dabd79ef2ac122e8416c7ec5cd15ef761057837b19c92	2026-02-16 23:24:14.325682+00	20240503130520_traces_index_updated_at	\N	\N	2026-02-16 23:24:14.324965+00	1
77fcd36a-54e2-443b-bd7c-95648f9e5a87	86eaf205ba5fd2130957536777d0aa00c8d15cdc2af896ea5b45ed5f26d690b6	2026-02-16 23:24:14.326543+00	20240508132621_scores_add_project_id	\N	\N	2026-02-16 23:24:14.326098+00	1
41a64bf2-e586-4327-a09c-406409235e10	644c6246091a13e8e908733347ffd699789d448bb3c80207e53b32223667a292	2026-02-16 23:24:14.327466+00	20240508132735_scores_add_projectid_index	\N	\N	2026-02-16 23:24:14.326714+00	1
4920ee7d-8d50-4d13-8212-4ff1f8c1f5fc	c1e8301b3c0ad83f46731fa6398565faa586ee89b5dc4ff22a2289a9f7c21d8e	2026-02-16 23:24:14.328587+00	20240508132736_scores_backfill_project_id	\N	\N	2026-02-16 23:24:14.327958+00	1
16d05147-6ad3-4039-a382-1028699616ce	3425cdbd747937bbb512b560a2b8132462d0412191a695e27dc9ae268f3d40f2	2026-02-16 23:24:14.329456+00	20240512151529_rename_memberships_to_project_memberships	\N	\N	2026-02-16 23:24:14.328763+00	1
776b34e7-1b61-41b2-b7a4-92d57d54f480	8030bef72fbca691d64e1fe5ca79e3f51e6137d85d73ec9afb97860ce81969dc	2026-02-16 23:24:14.366341+00	20240528214728_add_cursor_index_08	\N	\N	2026-02-16 23:24:14.365521+00	1
8f9a48fb-22cf-4870-a709-b3fdf3fcc9c9	d010f310671b164935b005b7949c29a46a2f14117e14060702f239cf3bb081cb	2026-02-16 23:24:14.334205+00	20240512155020_rename_enum_membership_role_to_project_role	\N	\N	2026-02-16 23:24:14.329638+00	1
a5a9ef62-fff9-4ae8-b603-b9d1d44d73ee	326dfa3b9b80dc55e40ab489fb74671a5c16a4aba84c9696b270880c7bfe46f6	2026-02-16 23:24:14.349074+00	20240524154058_scores_source_enum_add_annotation	\N	\N	2026-02-16 23:24:14.348604+00	1
22ba22a0-931d-44c8-a0d2-4245abb27735	a398b1ccdba2791a4646955f37522df929dd0e0a2d01603a068f70e096d2f53a	2026-02-16 23:24:14.335125+00	20240512155021_add_pricing_gpt4o	\N	\N	2026-02-16 23:24:14.334545+00	1
2dd03f2b-0df4-4e9a-97d8-3022e2935a56	f9750ea80adc2a175c4455a32779c5a607d741b71ca8354a18d9e8273b70b9a0	2026-02-16 23:24:14.336397+00	20240512155021_scores_drop_fk_on_traces_and_observations	\N	\N	2026-02-16 23:24:14.335455+00	1
a50f231e-d987-43ed-a3a3-4de51dd99a6a	dd6ec73dbd2dad9918cacba3f3b36aa35e88eb88a533ba89a9e0589eab28919d	2026-02-16 23:24:14.358622+00	20240528214727_add_cursor_new_columns_scores	\N	\N	2026-02-16 23:24:14.357933+00	1
b62f6828-f701-4514-aad2-9ffc0af0dee8	18525089d536b836d81e02dab68588e4fe2bf3d0a09e4c349d60db9bbed0cd49	2026-02-16 23:24:14.337363+00	20240512155022_scores_non_null_and_add_fk_project_id	\N	\N	2026-02-16 23:24:14.33656+00	1
2fbe8066-baba-4730-8592-04b9b14437d9	7c2d55160da3c5b58bd2710b99a9af01a92fccde03c15703fe59ab2d2c2965a0	2026-02-16 23:24:14.349967+00	20240524156058_scores_source_backfill_annotation_for_review	\N	\N	2026-02-16 23:24:14.349401+00	1
9ddcaf39-6a80-4f2c-a6a9-303c1fb65987	6f038363d06b8fe9ad5e5ffdebec33d4cde3591c65fe46175a4a821736637482	2026-02-16 23:24:14.338092+00	20240513082203_scores_unique_id_and_projectid_instead_of_id_and_traceid	\N	\N	2026-02-16 23:24:14.337531+00	1
898b3825-cf13-4805-9e30-d5acdc12ed1f	e39e28c4337fa35ab175c703d6ceda8a2d4b78d2bc616200201faff350c61455	2026-02-16 23:24:14.339289+00	20240513082204_scores_unique_id_and_projectid_instead_of_id_and_traceid_index	\N	\N	2026-02-16 23:24:14.338532+00	1
7fd273f4-d082-4237-80da-49d5fabd8d26	b8c134bdcba9a016d8ac79927a0d736c67c5bbf109ec584a15b0f6c38f50dc8d	2026-02-16 23:24:14.341288+00	20240513082205_observations_view_add_time_to_first_token	\N	\N	2026-02-16 23:24:14.339819+00	1
73ffeb84-5805-47b8-9748-6323bcbc8160	fff8108a9e3a443689ffc664fcb57f386343171b43607da12cc3ea46d7700585	2026-02-16 23:24:14.353144+00	20240524165931_scores_source_enum_drop_review	\N	\N	2026-02-16 23:24:14.350303+00	1
a8963474-510f-40e7-b1a0-f1b46d75289a	69b89171901be90854380c467ab615e82864cf72c128a011c0679b6e5af51e96	2026-02-16 23:24:14.342303+00	20240522081254_scores_add_author_user_id	\N	\N	2026-02-16 23:24:14.341733+00	1
33201b38-cddc-42b5-920a-47e76d4f0afb	1cba5ea95d8968dd4a1dfb6df8e844accbffca9d15e88aa87416eb6115b650e4	2026-02-16 23:24:14.343423+00	20240522095738_scores_add_author_user_id_index	\N	\N	2026-02-16 23:24:14.342627+00	1
ffc510f0-61a1-4bb1-98ae-ddb125d45c4a	75ba9583fb449a727d79158ed02d694b490c2d300c2da3eac7c79439966859d5	2026-02-16 23:24:14.363443+00	20240528214728_add_cursor_index_05	\N	\N	2026-02-16 23:24:14.362758+00	1
8d6e4607-8b06-4328-82ca-eb5581588bcb	439692a5f62df8e88a5aa6216e2019092d04f48a22f063861e20da6e3a278a9b	2026-02-16 23:24:14.346138+00	20240523142425_score_config_add_table	\N	\N	2026-02-16 23:24:14.3436+00	1
4eed09b9-43c7-43d7-94cd-b82e27f77b06	d186efeb838e34c83c0174fe727768a3b23487734d222ed8393b8cc0be4e83a3	2026-02-16 23:24:14.354015+00	20240524190433_job_executions_add_fk_index_config_id	\N	\N	2026-02-16 23:24:14.353311+00	1
bcce16ea-8cda-48d3-976e-602b92db6fd4	b6930ec8ce14d8a5e0d6792049f3af79bbd1ba1e4990ad2535ebc859edf856d9	2026-02-16 23:24:14.347194+00	20240523142524_scores_add_config_id_idx	\N	\N	2026-02-16 23:24:14.346458+00	1
abc84fb8-fb35-4136-8f9c-7d55412bf077	3df7e7fc9c22f17c9e8bdfd663cc2e5c473ec3e6e97129eebb989007943376d5	2026-02-16 23:24:14.348278+00	20240523142610_scores_add_fk_scores_config_id	\N	\N	2026-02-16 23:24:14.347361+00	1
95b455ba-88aa-49f4-8cf2-2cbee18838eb	952e15d6cf5306bb4802cc82fbe9f957196d77cc7f9035908014b205c5245232	2026-02-16 23:24:14.359616+00	20240528214728_add_cursor_index_01	\N	\N	2026-02-16 23:24:14.358806+00	1
3df17cac-5e72-45a8-a0f8-7e9cc66654e8	ea772561308b485138a96c9fde5666910bc8cfebc30763463acbade405198412	2026-02-16 23:24:14.355028+00	20240524190434_job_executions_add_fk_index_score_id	\N	\N	2026-02-16 23:24:14.354384+00	1
f728b705-c8a6-4838-b4aa-cab231caa14d	200a30bd560504185fd90be17c50db344bd1a71ecd599eefa5dc5d1b8504d0b5	2026-02-16 23:24:14.355883+00	20240524190435_job_executions_add_fk_index_trace_id	\N	\N	2026-02-16 23:24:14.355187+00	1
8ca7cc7d-d62a-4274-937b-64fef71079ba	28f7b81fda65228917bc40cbd676aa362538a3e32c328d7ee8069e6195f5319b	2026-02-16 23:24:14.3569+00	20240524190436_job_executions_index_created_at	\N	\N	2026-02-16 23:24:14.356195+00	1
19e65d59-ceed-4dfe-aee6-186d35f6e2c3	78b6379bbc520233c72ece8af40ed3e44c185479a4d65da104e3005394add5b7	2026-02-16 23:24:14.360674+00	20240528214728_add_cursor_index_02	\N	\N	2026-02-16 23:24:14.359976+00	1
48391bb3-613e-458b-af37-2e1efb0e1a1d	41f0f23e453c12cda5517c9f4da23112d7385ad3892f21114d2fcdd20ce1648c	2026-02-16 23:24:14.357757+00	20240528214726_add_cursor_new_columns_observations	\N	\N	2026-02-16 23:24:14.357239+00	1
6f8914c7-67d1-4b77-a5b8-66d194b7adc1	193aa18cb545aaa488d5d5c4852d61cd136eea2af6c4ffc9359dcf00cdda60c8	2026-02-16 23:24:14.361738+00	20240528214728_add_cursor_index_03	\N	\N	2026-02-16 23:24:14.361048+00	1
bf548230-a7fa-4ef9-9cb0-2f87aa736899	60796f59b086bb8e2c4f4901464cf99afc9baddbd4b9f67b492f93a0d192dac6	2026-02-16 23:24:14.364468+00	20240528214728_add_cursor_index_06	\N	\N	2026-02-16 23:24:14.363759+00	1
ae29af99-4266-494b-a91f-10516e106a3a	dca517a57077ee57fdbad8c599951dd6e12efbe9608579f211c750d46282ddd8	2026-02-16 23:24:14.362589+00	20240528214728_add_cursor_index_04	\N	\N	2026-02-16 23:24:14.361917+00	1
20889a40-bac1-4663-abac-f33069323aa3	43fabe3d60f20b7af6fa380afa5d3caee722ba94b2affffec300f06ae402870a	2026-02-16 23:24:14.370492+00	20240528214728_add_cursor_index_12	\N	\N	2026-02-16 23:24:14.369803+00	1
cd53d04d-1b97-46f4-94f3-1a8cce23c5bc	cd23d112029122106a7bae095c44e7d5ea702d5b5839898dde76855126b70e8d	2026-02-16 23:24:14.365354+00	20240528214728_add_cursor_index_07	\N	\N	2026-02-16 23:24:14.364655+00	1
ea761b1d-ca25-4c6f-9c4e-8464a4be8d56	ccc9e57838b1cb6a14d7ea38f87a363e256a9ebe54c7799f972880a05951679d	2026-02-16 23:24:14.369633+00	20240528214728_add_cursor_index_11	\N	\N	2026-02-16 23:24:14.368917+00	1
56c4ae29-8629-4be7-9822-4c1550e22d49	1e687237d6e6b1dbbc0627d78a9eacf6a25a7d9232db4841b7c1be90cfebadd2	2026-02-16 23:24:14.367225+00	20240528214728_add_cursor_index_09	\N	\N	2026-02-16 23:24:14.36651+00	1
4e730a27-fe19-4761-b4b6-2285025ccc7e	422f4d18f07108fd2a6a4bcae46f66a8afd1374c46f0b29efce0aab376e199a7	2026-02-16 23:24:14.36842+00	20240528214728_add_cursor_index_10	\N	\N	2026-02-16 23:24:14.367598+00	1
8a3a46f5-562b-449a-9f96-d7fee2c1ef0c	c94c666ca537a5dd8e8c1f8353c337990be02587535bcd31d793714391a35340	2026-02-16 23:24:14.371305+00	20240528214728_add_cursor_index_13	\N	\N	2026-02-16 23:24:14.370645+00	1
6855fb07-50ea-423d-a4cc-6d1646ff549b	372bd565f444f56abba3316b7642994ee2dab8d07a8e918366e235d8282573ed	2026-02-16 23:24:14.372276+00	20240528214728_add_cursor_index_14	\N	\N	2026-02-16 23:24:14.371642+00	1
8201fb99-5ac3-444a-ab70-d6cac01f0a36	e64d2f82e0e18bdeb80a75f75a19839cd5e0579e0c13336369191fe582592c98	2026-02-16 23:24:14.373098+00	20240528214728_add_cursor_index_15	\N	\N	2026-02-16 23:24:14.372448+00	1
c319cbbc-35ea-4b96-9192-2dc875d649fd	0a4105318c8c643b080415ad0d5566252acdefcbf7d95e10d93c0c7837f23202	2026-02-16 23:24:14.373957+00	20240528214728_add_cursor_index_16	\N	\N	2026-02-16 23:24:14.373261+00	1
03806614-90ab-4d1b-a35c-be47c9532a7c	c990b7a6ca81f32c14b6faa15ce64f673fb4ea950ee29295c0216aeb73505dac	2026-02-16 23:24:14.374846+00	20240528214728_add_cursor_index_17	\N	\N	2026-02-16 23:24:14.374128+00	1
d09b7417-15b2-4ead-88b6-82c3697ecda4	d3234c35c64e4ab9465ef5d699f2448147093e8d824e9287da35ae03b68276f5	2026-02-16 23:24:14.402874+00	20240710114043_score_configs_drop_empty_categories_array_for_numeric_scores	\N	\N	2026-02-16 23:24:14.402387+00	1
4d2c010b-330d-4ba9-9c88-a14dee604148	91bd416591a20ebf4a43e477e96840b27d9d719f228356836debf7aaf5a63c76	2026-02-16 23:24:14.375878+00	20240528214728_add_cursor_index_18	\N	\N	2026-02-16 23:24:14.375191+00	1
75505a01-937b-49f1-9f89-857396e3cded	08a92b24efa2f28043e5050f1071c39be9927e759fea2d68ed1a026f85457d25	2026-02-16 23:24:14.388008+00	20240618134129_add_batch_exports_table	\N	\N	2026-02-16 23:24:14.386396+00	1
6619f6be-73dd-4f4a-8a4b-8352e0d69557	c4155024314491d05b341db42b38ad22d35084502c842c3003f7e3a9a8278603	2026-02-16 23:24:14.37671+00	20240603212024_dataset_items_add_index_source_trace_id	\N	\N	2026-02-16 23:24:14.376033+00	1
5f552800-8955-45df-9a8a-3f7707467d51	c683e1a9bd10c23b0c47a8b24a4abf88a7c6c090f49288f1866308662811ca56	2026-02-16 23:24:14.377419+00	20240604133338_scores_add_index_name	\N	\N	2026-02-16 23:24:14.376881+00	1
f20de508-ce65-43b2-9742-1f6397114cf9	f0a4088b40007ed6f163f39d19c1656d29185f5002d32c902f73e872c3db953d	2026-02-16 23:24:14.394153+00	20240624133412_models_add_anthropic_3_5_sonnet	\N	\N	2026-02-16 23:24:14.393711+00	1
77f2f61f-8f74-4757-90d8-547ea330be25	a83f3d6ccaf505beb1d4e1e389e75f1e2f908e7f38083cdd0e9fe890b1a32ac5	2026-02-16 23:24:14.377997+00	20240604133339_score_data_type_add_boolean	\N	\N	2026-02-16 23:24:14.377572+00	1
d7e08b46-b6b4-41d0-bbe3-54729fac0f01	3dc892b57cc62544e92fd075401e0ddb9edd5536a014a1b0abcd8554c8c08f44	2026-02-16 23:24:14.388727+00	20240618164950_drop_observations_parent_observation_id_idx	\N	\N	2026-02-16 23:24:14.388162+00	1
c6501211-01bd-41d6-bc9e-4759d00a2ec1	4cfdd5861ab132ab402a50a8167c2f85b8dfcd59b9cf657c3a450822b428d421	2026-02-16 23:24:14.379497+00	20240606093356_drop_unused_pricings_table	\N	\N	2026-02-16 23:24:14.378376+00	1
50c5f9d5-a152-4986-bc2f-35573277f6d4	4dbdbcaf043e14669304021c929c5544297e4c1288814b373ac6180403a8e243	2026-02-16 23:24:14.380629+00	20240606133011_remove_trace_fkey_datasetrunitems	\N	\N	2026-02-16 23:24:14.379656+00	1
c2c349b9-00c5-4e12-99b7-46c0c5d1e07c	0e9d74c1cca79b04a49aea0a7590e985b40e87ab425919cf7625b5c9dbd08eae	2026-02-16 23:24:14.381273+00	20240607090858_pricings_add_latest_gemini_models	\N	\N	2026-02-16 23:24:14.380799+00	1
6fcb4ac1-7805-4ed2-88b9-3da42f72c35a	2966ccefa13d04e5bbe2fd2e6d199c46ea2915b4158b75b02840a072cbfc506d	2026-02-16 23:24:14.389446+00	20240618164951_drop_observations_updated_at_idx	\N	\N	2026-02-16 23:24:14.388892+00	1
336d488b-d8ac-49c6-aeac-c6ccb0e2cd88	844d238a2a7adc1bea26071ec926f5deae3bfad1a132498b539a8a73f7cd9b84	2026-02-16 23:24:14.381829+00	20240607212419_model_price_anthropic_via_google_vertex	\N	\N	2026-02-16 23:24:14.381433+00	1
9be5ca92-a7ff-45f1-9e7e-87b2c05686f0	bfb32da23d69cdd9b16e9b7a9397c199656f43a088d611bb870160be7162e456	2026-02-16 23:24:14.383159+00	20240611105521_llm_api_keys_custom_endpoints	\N	\N	2026-02-16 23:24:14.382066+00	1
d909debc-ca60-42f9-97e4-78d8593d338d	83c99f9d7f01ce1809e973fc571f11ce8f9a29c721832406b1632dc1340ce31a	2026-02-16 23:24:14.39885+00	20240704103901_scores_make_value_optional	\N	\N	2026-02-16 23:24:14.398351+00	1
bd0a16bf-3858-44fe-be39-1e97fb0b865a	e7110b354d5834e771980c2486a334501fc6c00d60d7489a771e6e32cdf113cf	2026-02-16 23:24:14.384469+00	20240611113517_backfill_manual_score_configs	\N	\N	2026-02-16 23:24:14.383323+00	1
b9c77353-db2a-463c-abd3-bec65d254924	cd37d3269447a71e8de058e7391986faf4d1ea88c7fc06e9e9de6d4d6754b7e8	2026-02-16 23:24:14.390212+00	20240618164952_drop_scores_updated_at_idx	\N	\N	2026-02-16 23:24:14.389606+00	1
a51365e1-9c30-4587-ab8f-c5bb15f0246c	5ffd2fdb41ff144cb14035a9feac869134180508f9ccf5c55f3d04a7c574f560	2026-02-16 23:24:14.385343+00	20240612101858_add_index_observations_project_id_prompt_id	\N	\N	2026-02-16 23:24:14.38462+00	1
f662bfd0-f8ca-425a-838c-587d718d6673	0c2ce80ed19bda8480a47a63222e518a74233937dd620d6856c85986e56459b5	2026-02-16 23:24:14.386183+00	20240617094803_observations_remove_prompt_fk_constraint	\N	\N	2026-02-16 23:24:14.385503+00	1
6d2c8a44-8374-41ed-b86c-e06623d2bb44	9d90da7cedae6dec276adee4484197e2a07a7007c17ccb309dfe1c228f0afb15	2026-02-16 23:24:14.394905+00	20240625103957_observations_add_calculated_cost_columns	\N	\N	2026-02-16 23:24:14.394322+00	1
80ac85ad-4bb1-4b86-9fb2-6080c27992e3	0f6b92ccc813c06eb9263e103d06c49bb31e5681c1eee935ce78b2302129e590	2026-02-16 23:24:14.391094+00	20240618164953_drop_traces_external_id_idx	\N	\N	2026-02-16 23:24:14.390542+00	1
85e98d1a-4025-4b3a-a390-607eda85f9ab	e8d748c34b7129a45445356f094c587d6d8abcf6e6b545fdb86c7343503db2a1	2026-02-16 23:24:14.391772+00	20240618164954_drop_traces_release_idx	\N	\N	2026-02-16 23:24:14.391245+00	1
d0d016ed-4f5a-410c-ae6a-0060efbca34f	189b316f8030f65f38d576d67418f1171c12e642b05d6368cd07b44253fdc7a6	2026-02-16 23:24:14.392479+00	20240618164955_drop_traces_updated_at_idx	\N	\N	2026-02-16 23:24:14.391955+00	1
328f9074-1dc0-48fc-8885-4f86d6bca57a	bd764616a4a133fcc775e140ec8b55f4cbbb553c69ab8d7f7f7095d0a32b2bc6	2026-02-16 23:24:14.395474+00	20240625103958_fix_model_match_gpt4_vision	\N	\N	2026-02-16 23:24:14.395059+00	1
4883d7b2-dee3-4108-ad08-6ee5ddb78268	54fce5d78c8c90abf77f97d3b1411ef0fa9346b08c113f6aa7127b4cba72bf13	2026-02-16 23:24:14.393343+00	20240618164956_create_traces_project_id_timestamp_idx	\N	\N	2026-02-16 23:24:14.392639+00	1
61bbd594-eebd-458d-b02a-aec4495718c4	1fcd4df49e013083ab4d3a0431ec979098eee48f568286401cde8fa4e3e3f5f8	2026-02-16 23:24:14.396122+00	20240703214747_models_anthropic_aws_bedrock	\N	\N	2026-02-16 23:24:14.39564+00	1
d0536563-4cde-437f-91e0-eb81f87d464b	09738b0d810db898fc0cef843f3ee6a2329a01dc47d03c7120013c70c37b1e33	2026-02-16 23:24:14.400245+00	20240705152639_traces_view_add_created_at_updated_at	\N	\N	2026-02-16 23:24:14.399015+00	1
b70ccb6d-5909-4b7a-869c-e312cdd3c973	bfe9303dbead984f51c5a743ca1106d5763600146ff1ed32de29676474887ef5	2026-02-16 23:24:14.398181+00	20240704103900_observations_view_read_from_calculated	\N	\N	2026-02-16 23:24:14.396496+00	1
295c67f1-ff03-44d8-9ef8-bccd13c0bb8f	9ba7731449b181af27b35098e2737877179ecb607c5ee1cdff8ba70c4e973036	2026-02-16 23:24:14.408214+00	20240718004923_datasets_tables_add_projectid_composite_key	\N	\N	2026-02-16 23:24:14.403661+00	1
913d599a-4919-47c5-8899-ef21be7a7320	b4c944a0fccea1e77f5b3026b958dfcf421d7c53794ef63289aa0ac3503b5f0b	2026-02-16 23:24:14.402194+00	20240705154048_observation_view_add_created_at_updated_at	\N	\N	2026-02-16 23:24:14.400599+00	1
eee6694e-f27d-46da-aefa-caf1f56daf95	ac968e7f259110955d27da88e05de49668356907f0832f7fe609738d515712f5	2026-02-16 23:24:14.403475+00	20240710114044_add_pricing_gpt4o_mini	\N	\N	2026-02-16 23:24:14.403039+00	1
471e1b71-bff9-4cca-8ac3-f46bd8925334	d0e5e3951923f398d25390a608624b8c7bb45349bd421441a0f502e406b04507	2026-02-16 23:24:14.410148+00	20240718011734_dataset_runs_drop_unique_dataset_id_name	\N	\N	2026-02-16 23:24:14.40954+00	1
0aee7744-021c-4c5d-bbfb-8db9d0157412	d4d71b3fd3254ac5a43f13e1ddffab6f77402911e682a8ee7d97f3db68c1c6d9	2026-02-16 23:24:14.409341+00	20240718011733_dataset_runs_add_unique_dataset_id_project_id_name copy	\N	\N	2026-02-16 23:24:14.40857+00	1
a1bc90d7-6402-4069-a781-0bab41259f6d	e30dba696d156c20754c34c32777b890361c2c1541b89ea17ec8f993eb9ae718	2026-02-16 23:24:14.412194+00	20240718011735_observation_view_add_prompt_name_and_version	\N	\N	2026-02-16 23:24:14.410339+00	1
99bd8135-0234-4ef4-bbb2-c1900888ebe6	c1608bf5817cd052359ecd3ec19096b5091247931bdc740b91b4ec97bcedeab9	2026-02-16 23:24:14.412818+00	20240807111358_models_add_openai_gpt_4o_2024_08_06	\N	\N	2026-02-16 23:24:14.412358+00	1
899e4282-ab66-41ad-ba44-32fe46b2b8df	8074e5eaabad18a6c7256d13fc7ae8639d038449d5dbb041143a95ca8d0730f1	2026-02-16 23:24:14.420406+00	20240807111359_add_organizations_main_migration	\N	\N	2026-02-16 23:24:14.413288+00	1
393c27af-97de-4992-93cb-8861eeb50858	ed0c0eb8eb8228cdac017ac8c31e31b6cc552161806825d38985afd9ee131e48	2026-02-16 23:24:14.421172+00	20240814223824_model_fix_text_embedding_3_large	\N	\N	2026-02-16 23:24:14.420752+00	1
5eeda4bc-b942-46cb-ac08-8d2e2e475eb4	1f7d8f99ea875bcdd3962ab0a13902548718c781f103712051c43e43f3811bd1	2026-02-16 23:24:14.433023+00	20240917183009_remove_covered_indexes_09	\N	\N	2026-02-16 23:24:14.432488+00	1
937672a5-594f-400f-a24f-c3b8d02133f3	b390309bf9420d1873574d39bfafefe1cc9efb4720ff93aa67e7e6b5ecdb806c	2026-02-16 23:24:14.42249+00	20240814233029_dataset_items_drop_fkey_on_traces_and_observations	\N	\N	2026-02-16 23:24:14.421508+00	1
0717e15c-9742-45bf-989d-65b71a172cc3	8c9d61879dd797ba022ada4f8c4ad9f20cf71f6c0e684096c0cdc55e25c192ac	2026-02-16 23:24:14.4245+00	20240815171916_add_comments	\N	\N	2026-02-16 23:24:14.422825+00	1
dd3c388e-0a3e-48fd-ab16-c4247bf91d70	2c12c46fa776893cdc6d215b0c6dec0531dc7bf8474454bf8de4d842ede48f24	2026-02-16 23:24:14.439835+00	20241009042557_auth_add_created_at_for_gitlab	\N	\N	2026-02-16 23:24:14.439315+00	1
dd44e364-42a8-41fe-9f5f-dee90db0902e	03510128bd751e5b3e5ea9599e2ad00cd7f24aed377607ebab1f56a639d73261	2026-02-16 23:24:14.425174+00	20240913095558_models_add_openai_o1_2024-09-12	\N	\N	2026-02-16 23:24:14.424713+00	1
26a843e8-80dd-4865-8844-43146eaee0a7	11f5f9d27072f867214018c24408b28c53e0c2acdba79492d3fe0ba7509d4954	2026-02-16 23:24:14.433877+00	20240917183010_remove_covered_indexes_10	\N	\N	2026-02-16 23:24:14.433337+00	1
5613e7df-eb7a-4be0-a480-029521a88cba	a5f429c21ec800e22377b61a192f208b8389718e4a950a4397c813b0af55adfc	2026-02-16 23:24:14.425783+00	20240913185822_account_add_refresh_token_expires_in	\N	\N	2026-02-16 23:24:14.425341+00	1
0111a583-e58a-4c46-bb44-72da040129fd	a91283903fab2398cf4119aee153ee91c04697fae59b653aa82d89413507502b	2026-02-16 23:24:14.426515+00	20240917183001_remove_covered_indexes_01	\N	\N	2026-02-16 23:24:14.425947+00	1
39086f29-d433-4f23-b62c-0421b1030f0a	16e13d2443a42819ab5693c1f11e1ff6503cea8c54462066c2ddd15e99b007fd	2026-02-16 23:24:14.427397+00	20240917183002_remove_covered_indexes_02	\N	\N	2026-02-16 23:24:14.426849+00	1
a28afec3-39df-413b-aea5-40fcae5b8caa	6654947f9c4c7d552dff50426840a1bdb54cb8def0ac9697603d0a3f97164338	2026-02-16 23:24:14.434777+00	20240917183011_remove_covered_indexes_11	\N	\N	2026-02-16 23:24:14.434192+00	1
d7332aa6-376e-4322-9df1-e895d7fd2649	5901031d78a2cbb177c0446288169a4485bba062cfc9a0a614e709931e150433	2026-02-16 23:24:14.428354+00	20240917183003_remove_covered_indexes_03	\N	\N	2026-02-16 23:24:14.427695+00	1
1a2eee53-2d8d-4ef8-9633-b3059a2ab0fe	ad2dd180dc79f9253d1cbe523725b9ef6f2d39c9457ab3528131eb3ddc23d9cc	2026-02-16 23:24:14.429104+00	20240917183004_remove_covered_indexes_04	\N	\N	2026-02-16 23:24:14.428518+00	1
2ea1b799-b0af-4b25-8199-4aeb9de876a3	47bd20bb7c5bba3d252474ae5bdf69136e40796fb5b0b9f9e988b29bb32cdae1	2026-02-16 23:24:14.456852+00	20241024121500_add_generations_cost_backfill_background_migration	\N	\N	2026-02-16 23:24:14.456339+00	1
86b52372-d820-482b-ae6b-fa0a515b2afb	81f3dbc2a12caef5e57f520b573742fe0d143b8914b47c43448638d4379fbd3d	2026-02-16 23:24:14.429854+00	20240917183005_remove_covered_indexes_05	\N	\N	2026-02-16 23:24:14.42926+00	1
4d7f8fca-9388-4624-a653-563e18f894ad	c4120d71f357eb5571b101e13961534009a45f5a3baefe51ac72f5cc1c31affb	2026-02-16 23:24:14.435495+00	20240917183012_remove_covered_indexes_12	\N	\N	2026-02-16 23:24:14.434948+00	1
2d348774-5fd4-4fe6-89e8-975e0d4f6847	7abe1457f2e45389e5b7b1cb321ea6e487bbe02cd5820186d681bdbc28668e2f	2026-02-16 23:24:14.430717+00	20240917183006_remove_covered_indexes_06	\N	\N	2026-02-16 23:24:14.430173+00	1
de8d6e59-ec79-413d-b16c-390d055dab33	851e507a8c51f16008faff917f9e457e321f4b090f6f197343683a837234f8f5	2026-02-16 23:24:14.431573+00	20240917183007_remove_covered_indexes_07	\N	\N	2026-02-16 23:24:14.431049+00	1
dfcfefaf-708d-4567-9de3-4245105edb10	58551031c2a3bbd0325b2610234e2316ee4c1d704ff42e402d65edd74ca5d120	2026-02-16 23:24:14.440453+00	20241009110720_scores_add_nullable_queue_id_column	\N	\N	2026-02-16 23:24:14.440007+00	1
fdf1bd64-c82c-45ee-bbe3-093f5afc4328	4f2bdda069ce30156aea5ad798c399078ddbd54b6839cb5f72e2c5d946352a28	2026-02-16 23:24:14.432323+00	20240917183008_remove_covered_indexes_08	\N	\N	2026-02-16 23:24:14.431745+00	1
ffeda064-dd4a-4369-b13b-f9b9875f4b54	cd4fa2a3c044b78666d0fc0011d89a5467101aa4322daa7873907f144c70f595	2026-02-16 23:24:14.436187+00	20240917183013_remove_covered_indexes_13	\N	\N	2026-02-16 23:24:14.435643+00	1
b4981839-ce8c-4171-9309-b51a8689464a	484041b7622a917effc1d608423692a072aa9d59e686627b367e4b9e9cffeed3	2026-02-16 23:24:14.45204+00	20241023110145_update_claude_sonnet_35	\N	\N	2026-02-16 23:24:14.451508+00	1
a9e43f2e-ebbe-4980-80c1-20c489379a89	d73184a6312e4e7bd67c689865f158eb03c3fda4acd2662aa38fc53ef7bd1052	2026-02-16 23:24:14.437067+00	20240917183014_remove_covered_indexes_14	\N	\N	2026-02-16 23:24:14.436552+00	1
f871774c-3d26-4bc7-9d0c-5cbfafb01f42	0dbe91562f26fe8f61373f8447175b7ab7ca248f30b9dba95bd577697a2370d8	2026-02-16 23:24:14.445287+00	20241009113245_add_annotation_queue	\N	\N	2026-02-16 23:24:14.440799+00	1
d4dff3fe-3e93-4d43-96d4-1aecb2ff0e9c	6cd7928e5bf79f84180c78fdd7479bfd81f1aced40338b17b12924be899bc234	2026-02-16 23:24:14.438091+00	20240917183015_remove_covered_indexes_15	\N	\N	2026-02-16 23:24:14.437546+00	1
9dea933d-9a77-48f3-ae71-eea1b26d8440	af5309595ed33080851fffd2de4c38aa3159df1e89dac976c9f228942b774edb	2026-02-16 23:24:14.43894+00	20240917183016_remove_covered_indexes_16	\N	\N	2026-02-16 23:24:14.438403+00	1
d27fdf40-55c3-455d-a437-a6b630d419f1	1473c5a5a9a83c6426e26cb71a3f78bff60527109eb8b7452d96afe76097012e	2026-02-16 23:24:14.446309+00	20241010120245_llm_keys_add_config	\N	\N	2026-02-16 23:24:14.44572+00	1
5fa12d3f-b4a4-48b9-882b-9af0b951d5d8	c4c3bcf2de95f7bfd8f19b53a4714f83520afa1117f251ed444d0a5322e7e217	2026-02-16 23:24:14.454568+00	20241024100928_add_prices_table	\N	\N	2026-02-16 23:24:14.452233+00	1
b8a2cb4b-1d0e-4a1c-b334-58c571a0c530	bb520543fe657f6f0d129953ce797619e91db7479eb154b0e7f9d10664da13fd	2026-02-16 23:24:14.45024+00	20241015110145_prompts_config_to_JSON	\N	\N	2026-02-16 23:24:14.44652+00	1
d9b66737-5aa7-4053-80ba-9a45804f4d94	ded2191a0871be7b5f9bba2c2f4385a756d567d2c6cf203e230fed2e872cb96a	2026-02-16 23:24:14.451164+00	20241022110145_add_claude_sonnet_35	\N	\N	2026-02-16 23:24:14.450578+00	1
17d240dc-cfb1-4240-87d0-e27086068dea	cd444613bc0a52ab579553655a9f12655fdf02373ae2195a49c6cb86fec64a11	2026-02-16 23:24:14.458153+00	20241024173700_add_observations_pg_to_ch_background_migration	\N	\N	2026-02-16 23:24:14.45774+00	1
0310a073-b81c-4c74-b7fd-2fbb4eedc265	44896f4896bfbfc0d1e7157def5d73912c40a49bc76334e71f7e4c9f385788dd	2026-02-16 23:24:14.456013+00	20241024111800_add_background_migrations_table	\N	\N	2026-02-16 23:24:14.454899+00	1
b4a394e7-3078-4f97-a1c1-d12189ee6329	df40a8b13f93c3f27304e151a2392b86dc6a1baaaa5979dad05b7fb7b5003f1c	2026-02-16 23:24:14.457569+00	20241024173000_add_traces_pg_to_ch_background_migration	\N	\N	2026-02-16 23:24:14.457197+00	1
c847f23f-bd36-4fa3-a748-20c185dcf931	192d7a00675ac998fbb295d08478ded69b4513286f5e3244af9f3ad99633c9a0	2026-02-16 23:24:14.459741+00	20241029130802_prices_drop_excess_index	\N	\N	2026-02-16 23:24:14.459125+00	1
610ebc79-f3a2-4fa2-834c-b37e7993e46a	5378729e79a3a38e8ff596e1c147116e4016aeef7e49c3b08cb2dadb0f835bab	2026-02-16 23:24:14.458685+00	20241024173800_add_scores_pg_to_ch_background_migration	\N	\N	2026-02-16 23:24:14.458318+00	1
2600ba6f-02d0-4947-861e-092009246dae	ef4fc49956097b140e83f2851fd27a551937c35de2d2bce13f38f049d8ff4cfa	2026-02-16 23:24:14.46043+00	20241104111600_background_migrations_add_state_column	\N	\N	2026-02-16 23:24:14.459963+00	1
f421cdc1-9556-43ba-9f5e-cdf5dce159bf	122dc03a7a54b31dbca09d8dfcc588d456cf15b7ef10691512fc384a79780683	2026-02-16 23:24:14.461344+00	20241105110900_add_claude_haiku_35	\N	\N	2026-02-16 23:24:14.460587+00	1
dea932be-ddd1-41fc-828e-278dd59fda30	5b702f5f10383113f05ee768a48c99dc6e3b8040899d9b814452a94a38aec33d	2026-02-16 23:24:14.46559+00	20241106122605_add_media_tables	\N	\N	2026-02-16 23:24:14.461522+00	1
8dc9b010-80cc-4b26-9711-52dda8ff4ac7	e6521663ec43b43a44681506fe0528386be64f557d51bb379ff564b908f8c715	2026-02-16 23:24:14.466856+00	20241114175010_job_executions_add_observation_dataset_item_cols	\N	\N	2026-02-16 23:24:14.466033+00	1
06fe43ca-3182-4e36-a49e-76250739ad85	ed1e394c590f6c66218a1c2d41558add7ee9e7ff67d86252a9abb580e5583b9b	2026-02-16 23:24:14.467567+00	20241125124029_add_chatgpt_4o_prices	\N	\N	2026-02-16 23:24:14.467027+00	1
\.


--
-- Data for Name: annotation_queue_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.annotation_queue_items (id, queue_id, object_id, object_type, status, locked_at, locked_by_user_id, annotator_user_id, completed_at, project_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: annotation_queues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.annotation_queues (id, name, description, score_config_ids, project_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: api_keys; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.api_keys (id, created_at, note, public_key, hashed_secret_key, display_secret_key, last_used_at, expires_at, project_id, fast_hashed_secret_key) FROM stdin;
key-jai-1	2026-02-17 02:35:38.046	Auto-provisioned for JAI Agent OS	pk-lf-jai-agent-os	$2a$10$jK/QoFpijgFEjmttK5x/d.BpSl8WmnKBeXzlGZ9byrY86ZtfboJm.	sk-lf...cret	\N	\N	proj-jai	d8a7a26ee72c3515ca952ea18e47025b269039e63c364149c613fb57ba79b581
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, created_at, updated_at, user_id, project_id, resource_type, resource_id, action, before, after, org_id, user_org_role, user_project_role) FROM stdin;
\.


--
-- Data for Name: background_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.background_migrations (id, name, script, args, finished_at, failed_at, failed_reason, worker_id, locked_at, state) FROM stdin;
32859a35-98f5-4a4a-b438-ebc579349e00	20241024_1216_add_generations_cost_backfill	addGenerationsCostBackfill	{}	\N	\N	\N	\N	\N	{}
5960f22a-748f-480c-b2f3-bc4f9d5d84bc	20241024_1730_migrate_traces_from_pg_to_ch	migrateTracesFromPostgresToClickhouse	{}	\N	\N	\N	\N	\N	{}
7526e7c9-0026-4595-af2c-369dfd9176ec	20241024_1737_migrate_observations_from_pg_to_ch	migrateObservationsFromPostgresToClickhouse	{}	\N	\N	\N	\N	\N	{}
94e50334-50d3-4e49-ad2e-9f6d92c85ef7	20241024_1738_migrate_scores_from_pg_to_ch	migrateScoresFromPostgresToClickhouse	{}	\N	\N	\N	\N	\N	{}
\.


--
-- Data for Name: batch_exports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batch_exports (id, created_at, updated_at, project_id, user_id, finished_at, expires_at, name, status, query, format, url, log) FROM stdin;
\.


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comments (id, project_id, object_type, object_id, created_at, updated_at, content, author_user_id) FROM stdin;
\.


--
-- Data for Name: cron_jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.cron_jobs (name, last_run, state, job_started_at) FROM stdin;
telemetry	2026-02-17 02:33:33.911	0d213f27-a9a4-417d-a7d0-8ef478fd1e24	\N
\.


--
-- Data for Name: dataset_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dataset_items (id, input, expected_output, source_observation_id, dataset_id, created_at, updated_at, status, source_trace_id, metadata, project_id) FROM stdin;
\.


--
-- Data for Name: dataset_run_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dataset_run_items (id, dataset_run_id, dataset_item_id, observation_id, created_at, updated_at, trace_id, project_id) FROM stdin;
\.


--
-- Data for Name: dataset_runs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dataset_runs (id, name, dataset_id, created_at, updated_at, metadata, description, project_id) FROM stdin;
\.


--
-- Data for Name: datasets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.datasets (id, name, project_id, created_at, updated_at, description, metadata) FROM stdin;
\.


--
-- Data for Name: eval_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.eval_templates (id, created_at, updated_at, project_id, name, version, prompt, model, model_params, vars, output_schema, provider) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.events (id, created_at, updated_at, project_id, data, url, method, headers) FROM stdin;
\.


--
-- Data for Name: job_configurations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_configurations (id, created_at, updated_at, project_id, job_type, eval_template_id, score_name, filter, target_object, variable_mapping, sampling, delay, status) FROM stdin;
\.


--
-- Data for Name: job_executions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_executions (id, created_at, updated_at, project_id, job_configuration_id, status, start_time, end_time, error, job_input_trace_id, job_output_score_id, job_input_dataset_item_id, job_input_observation_id) FROM stdin;
\.


--
-- Data for Name: llm_api_keys; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.llm_api_keys (id, created_at, updated_at, provider, display_secret_key, secret_key, project_id, base_url, adapter, custom_models, with_default_models, config) FROM stdin;
\.


--
-- Data for Name: media; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.media (id, sha_256_hash, project_id, created_at, updated_at, uploaded_at, upload_http_status, upload_http_error, bucket_path, bucket_name, content_type, content_length) FROM stdin;
\.


--
-- Data for Name: membership_invitations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.membership_invitations (id, email, project_id, invited_by_user_id, created_at, updated_at, org_id, org_role, project_role) FROM stdin;
\.


--
-- Data for Name: models; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.models (id, created_at, updated_at, project_id, model_name, match_pattern, start_date, input_price, output_price, total_price, unit, tokenizer_config, tokenizer_id) FROM stdin;
clrntkjgy000f08jx79v9g1xj	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4	(?i)^(gpt-4)$	\N	0.000030000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4", "tokensPerMessage": 3}	openai
clrkwk4cc000908l537kl0rx3	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-0613	(?i)^(gpt-4-0613)$	\N	0.000030000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-0613", "tokensPerMessage": 3}	openai
clrntkjgy000e08jx4x6uawoo	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-0314	(?i)^(gpt-4-0314)$	\N	0.000030000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-0314", "tokensPerMessage": 3}	openai
clrkvyzgw000308jue4hse4j9	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-32k	(?i)^(gpt-4-32k)$	\N	0.000060000000000000000000000000	0.000120000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-32k", "tokensPerMessage": 3}	openai
clrkwk4cb000108l5hwwh3zdi	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-32k-0613	(?i)^(gpt-4-32k-0613)$	\N	0.000060000000000000000000000000	0.000120000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-32k-0613", "tokensPerMessage": 3}	openai
clrntkjgy000d08jx0p4y9h4l	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-32k-0314	(?i)^(gpt-4-32k-0314)$	\N	0.000060000000000000000000000000	0.000120000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-32k-0314", "tokensPerMessage": 3}	openai
clrkwk4cc000a08l562uc3s9g	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo-instruct	(?i)^(gpt-)(35|3.5)(-turbo-instruct)$	\N	0.000001500000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 3}	openai
clrkwk4cb000408l576jl7koo	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo	(?i)^(gpt-)(35|3.5)(-turbo)$	2023-11-06 00:00:00	0.000001000000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 3}	openai
clrkwk4cb000208l59yvb9yq8	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo-1106	(?i)^(gpt-)(35|3.5)(-turbo-1106)$	\N	0.000001000000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-1106", "tokensPerMessage": 3}	openai
clrntkjgy000c08jxesb30p3f	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo	(?i)^(gpt-)(35|3.5)(-turbo)$	2023-06-27 00:00:00	0.000001500000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 3}	openai
clrkwk4cc000808l51xmk4uic	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo-0613	(?i)^(gpt-)(35|3.5)(-turbo-0613)$	\N	0.000001500000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-0613", "tokensPerMessage": 3}	openai
clrntkjgy000b08jx769q1bah	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo	(?i)^(gpt-)(35|3.5)(-turbo)$	\N	0.000002000000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": -1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 4}	openai
clrntkjgy000a08jx4e062mr0	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-3.5-turbo-0301	(?i)^(gpt-)(35|3.5)(-turbo-0301)$	\N	0.000002000000000000000000000000	0.000002000000000000000000000000	\N	TOKENS	{"tokensPerName": -1, "tokenizerModel": "gpt-3.5-turbo-0301", "tokensPerMessage": 4}	openai
clrntjt89000908jwhvkz5crm	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-embedding-ada-002	(?i)^(text-embedding-ada-002)$	2022-12-06 00:00:00	\N	\N	0.000000100000000000000000000000	TOKENS	{"tokenizerModel": "text-embedding-ada-002"}	openai
clrntjt89000908jwhvkz5crg	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-embedding-ada-002-v2	(?i)^(text-embedding-ada-002-v2)$	2022-12-06 00:00:00	\N	\N	0.000000100000000000000000000000	TOKENS	{"tokenizerModel": "text-embedding-ada-002"}	openai
clrntjt89000108jwcou1af71	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-ada-001	(?i)^(text-ada-001)$	\N	\N	\N	0.000004000000000000000000000000	TOKENS	{"tokenizerModel": "text-ada-001"}	openai
clrntjt89000208jwawjr894q	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-babbage-001	(?i)^(text-babbage-001)$	\N	\N	\N	0.000000500000000000000000000000	TOKENS	{"tokenizerModel": "text-babbage-001"}	openai
clrkvx5gp000108juaogs54ea	2026-02-16 23:24:14.253	2026-02-16 23:24:14.253	\N	gpt-4-turbo-vision	(?i)^(gpt-4(-\\d{4})?-vision-preview)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-vision-preview", "tokensPerMessage": 3}	openai
clrntjt89000308jw0jtfa4rs	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-curie-001	(?i)^(text-curie-001)$	\N	\N	\N	0.000020000000000000000000000000	TOKENS	{"tokenizerModel": "text-curie-001"}	openai
clrntjt89000408jwc2c93h6i	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-davinci-001	(?i)^(text-davinci-001)$	\N	\N	\N	0.000020000000000000000000000000	TOKENS	{"tokenizerModel": "text-davinci-001"}	openai
clrntjt89000508jw192m64qi	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-davinci-002	(?i)^(text-davinci-002)$	\N	\N	\N	0.000020000000000000000000000000	TOKENS	{"tokenizerModel": "text-davinci-002"}	openai
clrntjt89000608jw4m3x5s55	2026-02-16 23:24:14.256	2026-02-16 23:24:14.256	\N	text-davinci-003	(?i)^(text-davinci-003)$	\N	\N	\N	0.000020000000000000000000000000	TOKENS	{"tokenizerModel": "text-davinci-003"}	openai
clruwn3pc00010al7bl611c8o	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	text-embedding-3-small	(?i)^(text-embedding-3-small)$	\N	\N	\N	0.000000020000000000000000000000	TOKENS	{"tokenizerModel": "text-embedding-ada-002"}	openai
clruwnahl00030al7ab9rark7	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	gpt-3.5-turbo-0125	(?i)^(gpt-)(35|3.5)(-turbo-0125)$	\N	0.000000500000000000000000000000	0.000001500000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 3}	openai
clruwnahl00050al796ck3p44	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	gpt-4-0125-preview	(?i)^(gpt-4-0125-preview)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4", "tokensPerMessage": 3}	openai
clruwnahl00060al74fcfehas	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	gpt-4-turbo-preview	(?i)^(gpt-4-turbo-preview)$	\N	0.000030000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4", "tokensPerMessage": 3}	openai
clrs2dnql000108l46vo0gp2t	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	babbage-002	(?i)^(babbage-002)$	\N	0.000000400000000000000000000000	0.000001600000000000000000000000	\N	TOKENS	{"tokenizerModel": "babbage-002"}	openai
clrs2ds35000208l4g4b0hi3u	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	davinci-002	(?i)^(davinci-002)$	\N	0.000006000000000000000000000000	0.000012000000000000000000000000	\N	TOKENS	{"tokenizerModel": "davinci-002"}	openai
clrnwbota000908jsgg9mb1ml	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-instant-1	(?i)^(claude-instant-1)$	\N	0.000001630000000000000000000000	0.000005510000000000000000000000	\N	TOKENS	\N	claude
clrnwb41q000308jsfrac9uh6	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-instant-1.2	(?i)^(claude-instant-1.2)$	\N	0.000001630000000000000000000000	0.000005510000000000000000000000	\N	TOKENS	\N	claude
clrnwbd1m000508js4hxu6o7n	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-2.1	(?i)^(claude-2.1)$	\N	0.000008000000000000000000000000	0.000024000000000000000000000000	\N	TOKENS	\N	claude
clrnwb836000408jsallr6u11	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-2.0	(?i)^(claude-2.0)$	\N	0.000008000000000000000000000000	0.000024000000000000000000000000	\N	TOKENS	\N	claude
clrnwbg2b000608jse2pp4q2d	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-1.3	(?i)^(claude-1.3)$	\N	0.000008000000000000000000000000	0.000024000000000000000000000000	\N	TOKENS	\N	claude
clrnwbi9d000708jseiy44k26	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-1.2	(?i)^(claude-1.2)$	\N	0.000008000000000000000000000000	0.000024000000000000000000000000	\N	TOKENS	\N	claude
clrnwblo0000808jsc1385hdp	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	claude-1.1	(?i)^(claude-1.1)$	\N	0.000008000000000000000000000000	0.000024000000000000000000000000	\N	TOKENS	\N	claude
cls08r8sq000308jq14ae96f0	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	ft:gpt-3.5-turbo-1106	(?i)^(ft:)(gpt-3.5-turbo-1106:)(.+)(:)(.*)(:)(.+)$	\N	0.000003000000000000000000000000	0.000006000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-1106", "tokensPerMessage": 3}	openai
cls08rp99000408jqepxoakjv	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	ft:gpt-3.5-turbo-0613	(?i)^(ft:)(gpt-3.5-turbo-0613:)(.+)(:)(.*)(:)(.+)$	\N	0.000012000000000000000000000000	0.000016000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-0613", "tokensPerMessage": 3}	openai
cls08rv9g000508jq5p4z4nlr	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	ft:davinci-002	(?i)^(ft:)(davinci-002:)(.+)(:)(.*)(:)(.+)$$	\N	0.000012000000000000000000000000	0.000012000000000000000000000000	\N	TOKENS	{"tokenizerModel": "davinci-002"}	openai
cls08s2bw000608jq57wj4un2	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	ft:babbage-002	(?i)^(ft:)(babbage-002:)(.+)(:)(.*)(:)(.+)$$	\N	0.000001600000000000000000000000	0.000001600000000000000000000000	\N	TOKENS	{"tokenizerModel": "babbage-002"}	openai
cls0k4lqt000008ky1o1s8wd5	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	gemini-pro	(?i)^(gemini-pro)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0jni4t000008jk3kyy803r	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	chat-bison-32k	(?i)^(chat-bison-32k)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0iv12d000108l251gf3038	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	chat-bison	(?i)^(chat-bison)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0jmjt3000108l83ix86w0d	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	text-bison-32k	(?i)^(text-bison-32k)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0juygp000308jk2a6x9my2	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	text-bison	(?i)^(text-bison)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0jungb000208jk12gm4gk1	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	text-unicorn	(?i)^(text-unicorn)(@[a-zA-Z0-9]+)?$	\N	0.000002500000000000000000000000	0.000007500000000000000000000000	\N	CHARACTERS	\N	\N
cls1nyj5q000208l33ne901d8	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	textembedding-gecko	(?i)^(textembedding-gecko)(@[a-zA-Z0-9]+)?$	\N	\N	\N	0.000000100000000000000000000000	CHARACTERS	\N	\N
cls1nyyjp000308l31gxy1bih	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	textembedding-gecko-multilingual	(?i)^(textembedding-gecko-multilingual)(@[a-zA-Z0-9]+)?$	\N	\N	\N	0.000000100000000000000000000000	CHARACTERS	\N	\N
cls1nzjt3000508l3dnwad3g0	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	code-gecko	(?i)^(code-gecko)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls1nzwx4000608l38va7e4tv	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	code-bison	(?i)^(code-bison)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls1o053j000708l39f8g4bgs	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	code-bison-32k	(?i)^(code-bison-32k)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0j33v1000008joagkc4lql	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	codechat-bison-32k	(?i)^(codechat-bison-32k)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cls0jmc9v000008l8ee6r3gsd	2026-02-16 23:24:14.259	2026-02-16 23:24:14.259	\N	codechat-bison	(?i)^(codechat-bison)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
clrkwk4cb000308l5go4b6otm	2026-02-16 23:24:14.26	2026-02-16 23:24:14.26	\N	gpt-3.5-turbo-16k	(?i)^(gpt-)(35|3.5)(-turbo-16k)$	\N	0.000003000000000000000000000000	0.000004000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-16k", "tokensPerMessage": 3}	openai
clrntjt89000a08jw0gcdbd5a	2026-02-16 23:24:14.26	2026-02-16 23:24:14.26	\N	gpt-3.5-turbo-16k-0613	(?i)^(gpt-)(35|3.5)(-turbo-16k-0613)$	\N	0.000003000000000000000000000000	0.000004000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-16k-0613", "tokensPerMessage": 3}	openai
clruwnahl00040al78f1lb0at	2026-02-16 23:24:14.263	2026-02-16 23:24:14.263	\N	gpt-3.5-turbo	(?i)^(gpt-)(35|3.5)(-turbo)$	2024-02-16 00:00:00	0.000000500000000000000000000000	0.000001500000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo", "tokensPerMessage": 3}	openai
clsk9lntu000008jwfc51bbqv	2026-02-16 23:24:14.263	2026-02-16 23:24:14.263	\N	gpt-3.5-turbo-16k	(?i)^(gpt-)(35|3.5)(-turbo-16k)$	2024-02-16 00:00:00	0.000000500000000000000000000000	0.000001500000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-3.5-turbo-16k", "tokensPerMessage": 3}	openai
clsnq07bn000008l4e46v1ll8	2026-02-16 23:24:14.265	2026-02-16 23:24:14.265	\N	gpt-4-turbo-preview	(?i)^(gpt-4-turbo-preview)$	2023-11-06 00:00:00	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4", "tokensPerMessage": 3}	openai
clruwn76700020al7gp8e4g4l	2026-02-16 23:24:14.257	2026-02-16 23:24:14.257	\N	text-embedding-3-large	(?i)^(text-embedding-3-large)$	\N	\N	\N	0.000000130000000000000000000000	TOKENS	{"tokenizerModel": "text-embedding-ada-002"}	openai
cluv2sjeo000008ih0fv23hi0	2026-02-16 23:24:14.308	2026-02-16 23:24:14.308	\N	gemini-1.0-pro-latest	(?i)^(gemini-1.0-pro-latest)(@[a-zA-Z0-9]+)?$	\N	0.000000250000000000000000000000	0.000000500000000000000000000000	\N	CHARACTERS	\N	\N
cluv2subq000108ih2mlrga6a	2026-02-16 23:24:14.308	2026-02-16 23:24:14.308	\N	gemini-1.0-pro	(?i)^(gemini-1.0-pro)(@[a-zA-Z0-9]+)?$	2024-02-15 00:00:00	0.000000125000000000000000000000	0.000000375000000000000000000000	\N	CHARACTERS	\N	\N
cluv2sx04000208ihbek75lsz	2026-02-16 23:24:14.308	2026-02-16 23:24:14.308	\N	gemini-1.0-pro-001	(?i)^(gemini-1.0-pro-001)(@[a-zA-Z0-9]+)?$	2024-02-15 00:00:00	0.000000125000000000000000000000	0.000000375000000000000000000000	\N	CHARACTERS	\N	\N
cluv2szw0000308ihch3n79x7	2026-02-16 23:24:14.308	2026-02-16 23:24:14.308	\N	gemini-pro	(?i)^(gemini-pro)(@[a-zA-Z0-9]+)?$	2024-02-15 00:00:00	0.000000125000000000000000000000	0.000000375000000000000000000000	\N	CHARACTERS	\N	\N
cluv2t2x0000408ihfytl45l1	2026-02-16 23:24:14.308	2026-02-16 23:24:14.308	\N	gemini-1.5-pro-latest	(?i)^(gemini-1.5-pro-latest)(@[a-zA-Z0-9]+)?$	\N	0.000002500000000000000000000000	0.000007500000000000000000000000	\N	CHARACTERS	\N	\N
cluvpl4ls000008l6h2gx3i07	2026-02-16 23:24:14.309	2026-02-16 23:24:14.309	\N	gpt-4-turbo	(?i)^(gpt-4-turbo)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-1106-preview", "tokensPerMessage": 3}	openai
cluv2t5k3000508ih5kve9zag	2026-02-16 23:24:14.317	2026-02-16 23:24:14.317	\N	gpt-4-turbo-2024-04-09	(?i)^(gpt-4-turbo-2024-04-09)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-turbo-2024-04-09", "tokensPerMessage": 3}	openai
clrkvq6iq000008ju6c16gynt	2026-02-16 23:24:14.317	2026-02-16 23:24:14.317	\N	gpt-4-1106-preview	(?i)^(gpt-4-1106-preview)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-1106-preview", "tokensPerMessage": 3}	openai
clv2o2x0p000008jsf9afceau	2026-02-16 23:24:14.317	2026-02-16 23:24:14.317	\N	 gpt-4-preview	(?i)^(gpt-4-preview)$	\N	0.000010000000000000000000000000	0.000030000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4-turbo-preview", "tokensPerMessage": 3}	openai
b9854a5c92dc496b997d99d20	2026-02-16 23:24:14.335	2026-02-16 23:24:14.335	\N	gpt-4o	(?i)^(gpt-4o)$	\N	0.000005000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o", "tokensPerMessage": 3}	openai
b9854a5c92dc496b997d99d21	2026-02-16 23:24:14.335	2026-02-16 23:24:14.335	\N	gpt-4o-2024-05-13	(?i)^(gpt-4o-2024-05-13)$	\N	0.000005000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o-2024-05-13", "tokensPerMessage": 3}	openai
clx30djsn0000w9mzebiv41we	2026-02-16 23:24:14.381	2026-02-16 23:24:14.381	\N	gemini-1.5-flash	(?i)^(gemini-1.5-flash)(@[a-zA-Z0-9]+)?$	\N	\N	\N	\N	CHARACTERS	\N	\N
clx30hkrx0000w9mz7lqi0ial	2026-02-16 23:24:14.381	2026-02-16 23:24:14.381	\N	gemini-1.5-pro	(?i)^(gemini-1.5-pro)(@[a-zA-Z0-9]+)?$	\N	\N	\N	\N	CHARACTERS	\N	\N
cm3x0p8ev000008kyd96800c8	2026-02-16 23:24:14.467	2026-02-16 23:24:14.467	\N	chatgpt-4o-latest	(?i)^(chatgpt-4o-latest)$	\N	0.000005000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o", "tokensPerMessage": 3}	openai
cltr0w45b000008k1407o9qv1	2026-02-16 23:24:14.289	2026-02-16 23:24:14.289	\N	claude-3-haiku-20240307	(?i)^(claude-3-haiku-20240307|anthropic\\.claude-3-haiku-20240307-v1:0|claude-3-haiku@20240307)$	\N	0.000000250000000000000000000000	0.000001250000000000000000000000	\N	TOKENS	\N	claude
cltgy0pp6000108le56se7bl3	2026-02-16 23:24:14.285	2026-02-16 23:24:14.285	\N	claude-3-sonnet-20240229	(?i)^(claude-3-sonnet-20240229|anthropic\\.claude-3-sonnet-20240229-v1:0|claude-3-sonnet@20240229)$	\N	0.000003000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	\N	claude
cltgy0iuw000008le3vod1hhy	2026-02-16 23:24:14.285	2026-02-16 23:24:14.285	\N	claude-3-opus-20240229	(?i)^(claude-3-opus-20240229|anthropic\\.claude-3-opus-20240229-v1:0|claude-3-opus@20240229)$	\N	0.000015000000000000000000000000	0.000075000000000000000000000000	\N	TOKENS	\N	claude
clxt0n0m60000pumz1j5b7zsf	2026-02-16 23:24:14.394	2026-02-16 23:24:14.394	\N	claude-3-5-sonnet-20240620	(?i)^(claude-3-5-sonnet-20240620|anthropic\\.claude-3-5-sonnet-20240620-v1:0|claude-3-5-sonnet@20240620)$	\N	0.000003000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	\N	claude
clyrjp56f0000t0mzapoocd7u	2026-02-16 23:24:14.403	2026-02-16 23:24:14.403	\N	gpt-4o-mini	(?i)^(gpt-4o-mini)$	\N	0.000000150000000000000000000000	0.000000600000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o", "tokensPerMessage": 3}	openai
clyrjpbe20000t0mzcbwc42rg	2026-02-16 23:24:14.403	2026-02-16 23:24:14.403	\N	gpt-4o-mini-2024-07-18	(?i)^(gpt-4o-mini-2024-07-18)$	\N	0.000000150000000000000000000000	0.000000600000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o", "tokensPerMessage": 3}	openai
clzjr85f70000ymmzg7hqffra	2026-02-16 23:24:14.413	2026-02-16 23:24:14.413	\N	gpt-4o-2024-08-06	(?i)^(gpt-4o-2024-08-06)$	\N	0.000002500000000000000000000000	0.000010000000000000000000000000	\N	TOKENS	{"tokensPerName": 1, "tokenizerModel": "gpt-4o", "tokensPerMessage": 3}	openai
cm10ivcdp0000gix7lelmbw80	2026-02-16 23:24:14.425	2026-02-16 23:24:14.425	\N	o1-preview	(?i)^(o1-preview)$	\N	0.000015000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	\N	\N
cm10ivo130000n8x7qopcjjcg	2026-02-16 23:24:14.425	2026-02-16 23:24:14.425	\N	o1-preview-2024-09-12	(?i)^(o1-preview-2024-09-12)$	\N	0.000015000000000000000000000000	0.000060000000000000000000000000	\N	TOKENS	\N	\N
cm10ivwo40000r1x7gg3syjq0	2026-02-16 23:24:14.425	2026-02-16 23:24:14.425	\N	o1-mini	(?i)^(o1-mini)$	\N	0.000003000000000000000000000000	0.000012000000000000000000000000	\N	TOKENS	\N	\N
cm10iw6p20000wgx7it1hlb22	2026-02-16 23:24:14.425	2026-02-16 23:24:14.425	\N	o1-mini-2024-09-12	(?i)^(o1-mini-2024-09-12)$	\N	0.000003000000000000000000000000	0.000012000000000000000000000000	\N	TOKENS	\N	\N
cm2krz1uf000208jjg5653iud	2026-02-16 23:24:14.451	2026-02-16 23:24:14.451	\N	claude-3.5-sonnet-20241022	(?i)^(claude-3-5-sonnet-20241022|anthropic\\.claude-3-5-sonnet-20241022-v2:0|claude-3-5-sonnet-V2@20241022)$	\N	0.000003000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	\N	claude
cm2ks2vzn000308jjh4ze1w7q	2026-02-16 23:24:14.451	2026-02-16 23:24:14.451	\N	claude-3.5-sonnet-latest	(?i)^(claude-3-5-sonnet-latest)$	\N	0.000003000000000000000000000000	0.000015000000000000000000000000	\N	TOKENS	\N	claude
cm34aq60d000207ml0j1h31ar	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	\N	claude-3-5-haiku-20241022	(?i)^(claude-3-5-haiku-20241022|anthropic\\.claude-3-5-haiku-20241022-v1:0|claude-3-5-haiku-V1@20241022)$	\N	0.000001000000000000000000000000	0.000005000000000000000000000000	\N	TOKENS	\N	claude
cm34aqb9h000307ml6nypd618	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	\N	claude-3.5-haiku-latest	(?i)^(claude-3-5-haiku-latest)$	\N	0.000001000000000000000000000000	0.000005000000000000000000000000	\N	TOKENS	\N	claude
\.


--
-- Data for Name: observation_media; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.observation_media (id, project_id, created_at, updated_at, media_id, trace_id, observation_id, field) FROM stdin;
\.


--
-- Data for Name: observations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.observations (id, name, start_time, end_time, parent_observation_id, type, trace_id, metadata, model, "modelParameters", input, output, level, status_message, completion_start_time, completion_tokens, prompt_tokens, total_tokens, version, project_id, created_at, unit, prompt_id, input_cost, output_cost, total_cost, internal_model, updated_at, calculated_input_cost, calculated_output_cost, calculated_total_cost, internal_model_id) FROM stdin;
7722a620-2ab4-4aa7-b0a9-f0734a1bdcfd	chat-completion	2026-02-17 02:57:31.452	2026-02-17 02:57:31.452	\N	GENERATION	e5486500-0188-4cdb-82fb-1de249a347ab	{"cost_usd": 0, "latency_ms": 2356.65}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "What is procurement spend analysis? Answer in 2 sentences."}]}	{"content": "Procurement spend analysis is the systematic process"}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:57:31.471	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:57:31.471	\N	\N	\N	\N
f449ede2-fe78-4937-be37-5cc6a02bcf81	chat-completion	2026-02-17 02:57:58.268	2026-02-17 02:57:58.268	\N	GENERATION	a6401437-09bd-44d3-9dba-78f28defb44e	{"cost_usd": 0, "latency_ms": 2156.49}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "Compare the top 3 supplier risk factors for a manufacturing company. Be concise."}]}	{"content": "Here are the top 3 supplier risk factors for a manufacturing company, concisely compared:\\n\\n1.  **Financial Stability:**  High risk if suppliers are financially unstable, leading to potential supply disruptions, quality issues (cutting corners), or even bankruptcy.  Impacts production continuity.\\n\\n2.  **Operational Capacity & Performance:**  Insufficient capacity, poor quality control, or unreliable delivery schedules directly impact the manufacturer's ability to meet demand and maintain quality standards.  Affects lead times and customer satisfaction.\\n\\n3.  **Geopolitical & Environmental Factors:**  Political instability, trade wars, natural disasters, and regulatory changes in the supplier's region can severely disrupt supply chains, increase costs, and create ethical/compliance concerns.  Impacts long-term supply security and reputation."}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:57:58.281	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:57:58.281	\N	\N	\N	\N
7f5ae2b8-a302-4d8a-ab31-6cd2500e214f	chat-completion	2026-02-17 02:58:00.701	2026-02-17 02:58:00.701	\N	GENERATION	da842297-2a85-4645-a903-be97a90df9d3	{"cost_usd": 0, "latency_ms": 2333.14}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "Draft a short email to a supplier requesting updated pricing for Q3 2025."}]}	{"content": "Subject: Request for Q3 2025 Pricing"}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:00.717	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:00.717	\N	\N	\N	\N
a1afff73-58e5-4f86-ab95-7536d6e8e038	chat-completion	2026-02-17 02:58:03.998	2026-02-17 02:58:03.998	\N	GENERATION	1e509156-5f87-419c-a7a1-747820bc579f	{"cost_usd": 0, "latency_ms": 3214.36}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "What are the key KPIs for measuring procurement efficiency?"}]}	{"content": "Measuring procurement efficiency is crucial for optimizing spending, improving supplier relationships, and ultimately boosting profitability. Here are some key KPIs (Key Performance Indicators) for measuring procurement efficiency, categorized for clarity:\\n\\n**I. Cost Savings & Value Generation:**\\n\\n*   **Cost Savings Realized:**  This is the most fundamental KPI. It measures the actual savings achieved through procurement initiatives (negotiations, sourcing strategies, etc.) compared to a baseline (e.g., previous year's spending, market price).  Expressed as a percentage or absolute value.\\n    *   **Formula:** `[(Baseline Spend - Actual Spend) / Baseline Spend] * 100`\\n*   **Total Cost of Ownership (TCO):**  Goes beyond the initial purchase price to include all costs associated with acquiring, using, maintaining, and disposing of a product or service.  Tracking TCO helps identify hidden costs and make informed decisions.\\n*   **Return on Investment (ROI) of Procurement:** Measures the profitability of procurement investments (e.g., technology, training, strategic sourcing).\\n    *   **Formula:** `[(Gain from Investment - Cost of Investment) / Cost of Investment] * 100`\\n*   **Spend Under Management:**  The percentage of total company spend that procurement actively manages and influences.  A higher percentage generally indicates greater control and potential for savings.\\n    *   **Formula:** `(Managed Spend / Total Spend) * "}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:04.013	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:04.013	\N	\N	\N	\N
59d1480c-7ee1-4179-a574-9bc261fc2fcb	chat-completion	2026-02-17 02:58:06.604	2026-02-17 02:58:06.604	\N	GENERATION	ac4948fd-cf64-4e91-9da2-cfe8a64d08af	{"cost_usd": 0, "latency_ms": 2506.57}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "Summarize the risks of single-source supplier dependency in 3 bullet points."}]}	{"content": "Here are the risks of single-source supplier dependency:"}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:06.619	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:06.619	\N	\N	\N	\N
19fcc9ec-5826-40a5-8169-5df6791bae8a	chat-completion	2026-02-17 02:58:09.016	2026-02-17 02:58:09.016	\N	GENERATION	9053e204-083c-4287-97f2-f4a7db95934b	{"cost_usd": 0, "latency_ms": 2322.49}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "What are the top 5 clauses to review in a SaaS vendor contract?"}]}	{"content": "When reviewing a SaaS vendor contract, focusing"}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:09.042	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:09.042	\N	\N	\N	\N
87fb3cfe-36f1-4511-80a4-645d0896df6b	chat-completion	2026-02-17 02:58:11.232	2026-02-17 02:58:11.232	\N	GENERATION	a94a9b87-bec2-40a3-a49a-380cb2422abd	{"cost_usd": 0, "latency_ms": 2113.78}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "Calculate: Supplier A costs $50/unit for 10000 units + $5000 shipping. Supplier B costs $45/unit for 10000 units + $8000 shipping + $3000 setup. Which is cheaper?"}]}	{"content": "Let's calculate the total cost for each supplier:\\n\\n**Supplier A:**\\n\\n*   Unit Cost: $50/unit * 10000 units = $500,000\\n*   Shipping: $5,000\\n*   Total Cost: $500,000 + $5,000 = $505,000\\n\\n**Supplier B:**\\n\\n*   Unit Cost: $45/unit * 10000 units = $450,000\\n*   Shipping: $8,000\\n*   Setup: $3,000\\n*   Total Cost: $450,000 + $8,000 + $3,000 = $461,000\\n\\n**Comparison:**\\n\\nSupplier A: $505,000\\nSupplier B: $461,000\\n\\n**Conclusion:** Supplier B is cheaper."}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:11.247	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:11.247	\N	\N	\N	\N
9b74bb39-d63d-4fe2-90b9-fa01d1b5cdd1	chat-completion	2026-02-17 02:58:19.006	2026-02-17 02:58:19.006	\N	GENERATION	ec7cf65b-2ad8-4796-89d2-77f2fe661560	{"cost_usd": 0, "latency_ms": 681.81}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "Say hello"}]}	{"content": "Hello! How can I help you today?"}	DEFAULT	\N	\N	0	0	0	\N	proj-jai	2026-02-17 02:58:19.017	TOKENS	\N	\N	\N	\N	\N	2026-02-17 02:58:19.017	\N	\N	\N	\N
be1ec62b-f3b5-4daf-8c7b-8d640db0f9d9	chat-completion	2026-02-17 03:00:37.197	2026-02-17 03:00:37.197	\N	GENERATION	8329819f-3a5f-4e80-b013-9f5a25c95b23	{"cost_usd": 0.000119, "latency_ms": 2571.19}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "What are 3 benefits of e-procurement systems?"}]}	{"content": "Here are 3 key"}	DEFAULT	\N	\N	196	12	208	\N	proj-jai	2026-02-17 03:00:37.213	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:00:37.213	\N	\N	\N	\N
406bf170-2b84-4d62-bae1-657638c37cdd	chat-completion	2026-02-17 03:00:51.312	2026-02-17 03:00:51.312	\N	GENERATION	ccd88631-9b11-4a6c-b901-c9aab368c7c3	{"cost_usd": 0.000163, "latency_ms": 1278.17}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "Compare centralized vs decentralized procurement models in 3 sentences."}]}	{"content": "Centralized procurement leverages economies of scale and standardized processes for cost savings and better control, but can be less responsive to local needs. Decentralized procurement allows for greater flexibility and responsiveness to specific departmental requirements, but may result in higher costs and inconsistent practices. Ultimately, the best model depends on an organization's size, structure, and strategic priorities, often leading to hybrid approaches."}	DEFAULT	\N	\N	76	11	87	\N	proj-jai	2026-02-17 03:00:51.329	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:00:51.329	\N	\N	\N	\N
892c08e1-e0b2-4cf5-a8e7-fea223ed20a3	chat-completion	2026-02-17 03:00:53.34	2026-02-17 03:00:53.34	\N	GENERATION	8dfc4eca-acb3-42a3-8d75-9d93fa1d35af	{"cost_usd": 0.000134, "latency_ms": 1968.89}	gemini-2.5-flash	\N	{"messages": [{"role": "system", "content": "You are a procurement AI assistant."}, {"role": "user", "content": "Draft a 3-line RFQ summary for office supplies vendor selection."}]}	{"content": "Request for Quotation (RFQ) for the procurement of general office supplies. We seek competitive pricing, high-quality products, and reliable delivery from qualified vendors. Submit detailed proposals outlining catalogs, pricing, and service capabilities for primary vendor selection."}	DEFAULT	\N	\N	218	22	240	\N	proj-jai	2026-02-17 03:00:53.353	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:00:53.353	\N	\N	\N	\N
67239d9f-7402-4323-ad92-f8e9b6890203	chat-completion	2026-02-17 03:00:56.651	2026-02-17 03:00:56.651	\N	GENERATION	d50acc87-08fd-430f-85f8-505f7a3a25fb	{"cost_usd": 0.000611, "latency_ms": 3257.91}	gemini-2.0-flash-001	\N	{"messages": [{"role": "user", "content": "List 5 red flags in a supplier audit report."}]}	{"content": "Here are 5 red flags that might appear in a supplier audit report, indicating potential problems and requiring further investigation:\\n\\n1.  **Consistent Non-Compliance with Critical Requirements:** This is a major red flag. If the audit report consistently shows non-compliance with critical requirements related to safety, quality, legality, or ethical standards (e.g., food safety hazards, child labor, environmental regulations), it indicates a systemic problem.  Isolated minor issues are understandable, but repeated or significant failures in critical areas suggest a lack of commitment or capability.\\n\\n2.  **Data Falsification or Incomplete Records:**  Any evidence of falsified records, missing documentation, or attempts to conceal information is a serious red flag. This suggests a lack of transparency and a willingness to deceive, making it difficult to trust the supplier's processes and products.  Examples include altered production logs, missing calibration records, or discrepancies between reported and observed practices.\\n\\n3.  **Poor Working Conditions and Labor Rights Violations:**  Findings related to unsafe working conditions, inadequate worker training, forced labor, or violations of minimum wage laws are significant red flags. These issues not only pose ethical concerns but can also lead to production disruptions, legal liabilities, and reputational damage for your company.\\n\\n4.  **Lack of Corrective Action Implementation:**  If previous audit reports identified issues, and the current report shows little or no progress in implementing corrective actions, it indicates a lack of commitment to improvement.  "}	DEFAULT	\N	\N	300	11	311	\N	proj-jai	2026-02-17 03:00:56.664	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:00:56.664	\N	\N	\N	\N
9f9ac31a-165f-4000-8b11-e63705e764dc	chat-completion	2026-02-17 03:00:58.867	2026-02-17 03:00:58.867	\N	GENERATION	c7cb16dc-cb14-4b13-a2d4-6c97ed1078b4	{"cost_usd": 0.00012, "latency_ms": 2163.05}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "What is tail spend and why does it matter for procurement teams?"}]}	{"content": "**Tail spend**"}	DEFAULT	\N	\N	196	13	209	\N	proj-jai	2026-02-17 03:00:58.878	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:00:58.878	\N	\N	\N	\N
03ff44f6-add4-47c4-8ce1-80b0ebaebb3a	chat-completion	2026-02-17 03:05:24.592	2026-02-17 03:05:24.592	\N	GENERATION	d86ad628-6767-4032-b8b5-72e061daead3	{"cost_usd": 0.000059, "latency_ms": 1745.89}	gemini-2.5-flash	\N	{"messages": [{"role": "user", "content": "Explain maverick spending in procurement in one sentence."}]}	{"content": "Maverick spending in"}	DEFAULT	\N	\N	96	10	106	\N	proj-jai	2026-02-17 03:05:24.609	TOKENS	\N	\N	\N	\N	\N	2026-02-17 03:05:24.609	\N	\N	\N	\N
\.


--
-- Data for Name: organization_memberships; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organization_memberships (id, org_id, user_id, role, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organizations (id, name, created_at, updated_at, cloud_config) FROM stdin;
org-jai	JAI Agent OS	2026-02-17 02:35:38.046	2026-02-17 02:35:38.046	\N
\.


--
-- Data for Name: posthog_integrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.posthog_integrations (project_id, encrypted_posthog_api_key, posthog_host_name, last_sync_at, enabled, created_at) FROM stdin;
\.


--
-- Data for Name: prices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.prices (id, created_at, updated_at, model_id, usage_type, price) FROM stdin;
cm34ax6mc000008jkfqed92mb	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	cm34aq60d000207ml0j1h31ar	input	0.000001000000000000000000000000
cm34axb2o000108jk09wn9b47	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	cm34aqb9h000307ml6nypd618	input	0.000001000000000000000000000000
cm34axeie000208jk8b2ke2t8	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	cm34aq60d000207ml0j1h31ar	output	0.000005000000000000000000000000
cm34axi67000308jk7x1a7qko	2026-02-16 23:24:14.461	2026-02-16 23:24:14.461	cm34aqb9h000307ml6nypd618	output	0.000005000000000000000000000000
cm3x0psrz000108kydpxg9o2k	2026-02-16 23:24:14.467	2026-02-16 23:24:14.467	cm3x0p8ev000008kyd96800c8	input	0.000005000000000000000000000000
cm3x0pyt7000208ky8737gdla	2026-02-16 23:24:14.467	2026-02-16 23:24:14.467	cm3x0p8ev000008kyd96800c8	output	0.000015000000000000000000000000
\.


--
-- Data for Name: project_memberships; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_memberships (project_id, user_id, created_at, updated_at, org_membership_id, role) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.projects (id, created_at, name, updated_at, org_id) FROM stdin;
proj-jai	2026-02-17 02:35:38.046	jai-agent-os	2026-02-17 02:35:38.046	org-jai
\.


--
-- Data for Name: prompts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.prompts (id, created_at, updated_at, project_id, created_by, name, version, is_active, config, prompt, type, tags, labels) FROM stdin;
\.


--
-- Data for Name: score_configs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.score_configs (id, created_at, updated_at, project_id, name, data_type, is_archived, min_value, max_value, categories, description) FROM stdin;
\.


--
-- Data for Name: scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scores (id, "timestamp", name, value, observation_id, trace_id, comment, source, project_id, author_user_id, config_id, data_type, string_value, created_at, updated_at, queue_id) FROM stdin;
\.


--
-- Data for Name: sso_configs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sso_configs (domain, created_at, updated_at, auth_provider, auth_config) FROM stdin;
\.


--
-- Data for Name: trace_media; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.trace_media (id, project_id, created_at, updated_at, media_id, trace_id, field) FROM stdin;
\.


--
-- Data for Name: trace_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.trace_sessions (id, created_at, updated_at, project_id, bookmarked, public) FROM stdin;
demo-session-1	2026-02-17 02:57:29.124	2026-02-17 02:57:29.124	proj-jai	f	f
demo-session-2	2026-02-17 02:57:56.124	2026-02-17 02:57:56.124	proj-jai	f	f
demo-session-3	2026-02-17 02:57:58.377	2026-02-17 02:57:58.377	proj-jai	f	f
demo-session-4	2026-02-17 02:58:00.793	2026-02-17 02:58:00.793	proj-jai	f	f
demo-session-5	2026-02-17 02:58:06.703	2026-02-17 02:58:06.703	proj-jai	f	f
demo-session-6	2026-02-17 02:58:09.129	2026-02-17 02:58:09.129	proj-jai	f	f
demo-fresh-1	2026-02-17 03:00:34.666	2026-02-17 03:00:34.666	proj-jai	f	f
demo-fresh-2	2026-02-17 03:00:50.047	2026-02-17 03:00:50.047	proj-jai	f	f
demo-fresh-3	2026-02-17 03:00:51.382	2026-02-17 03:00:51.382	proj-jai	f	f
demo-fresh-4	2026-02-17 03:00:53.403	2026-02-17 03:00:53.403	proj-jai	f	f
demo-final	2026-02-17 03:05:22.87	2026-02-17 03:05:22.87	proj-jai	f	f
\.


--
-- Data for Name: traces; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.traces (id, "timestamp", name, project_id, metadata, external_id, user_id, release, version, public, bookmarked, input, output, session_id, tags, created_at, updated_at) FROM stdin;
e5486500-0188-4cdb-82fb-1de249a347ab	2026-02-17 02:57:29.127	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-bdc1636f37c3"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "What is procurement spend analysis? Answer in 2 sentences."}], "temperature": 0.7}	{"model": "gemini-2.5-flash", "tokens": 0, "content": "Procurement spend analysis is the systematic process"}	demo-session-1	{gateway,gemini-2.5-flash}	2026-02-17 02:57:29.127	2026-02-17 02:57:31.481
a6401437-09bd-44d3-9dba-78f28defb44e	2026-02-17 02:57:56.126	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-01d91dd3fa6e"}	\N	bob@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "Compare the top 3 supplier risk factors for a manufacturing company. Be concise."}], "temperature": 0.5}	{"model": "gemini-2.0-flash-001", "tokens": 0, "content": "Here are the top 3 supplier risk factors for a manufacturing company, concisely compared:\\n\\n1.  **Financial Stability:**  High risk if suppliers are financially unstable, leading to potential supply di"}	demo-session-2	{gateway,gemini-2.0-flash-001}	2026-02-17 02:57:56.126	2026-02-17 02:57:58.291
da842297-2a85-4645-a903-be97a90df9d3	2026-02-17 02:57:58.378	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-407f1bc47bbe"}	\N	carol@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Draft a short email to a supplier requesting updated pricing for Q3 2025."}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 0, "content": "Subject: Request for Q3 2025 Pricing"}	demo-session-3	{gateway,gemini-2.5-flash}	2026-02-17 02:57:58.378	2026-02-17 02:58:00.726
1e509156-5f87-419c-a7a1-747820bc579f	2026-02-17 02:58:00.795	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-c940bfa67669"}	\N	dave@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "What are the key KPIs for measuring procurement efficiency?"}], "temperature": 0.5}	{"model": "gemini-2.0-flash-001", "tokens": 0, "content": "Measuring procurement efficiency is crucial for optimizing spending, improving supplier relationships, and ultimately boosting profitability. Here are some key KPIs (Key Performance Indicators) for me"}	demo-session-4	{gateway,gemini-2.0-flash-001}	2026-02-17 02:58:00.795	2026-02-17 02:58:04.024
ac4948fd-cf64-4e91-9da2-cfe8a64d08af	2026-02-17 02:58:04.107	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-42830d277437"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Summarize the risks of single-source supplier dependency in 3 bullet points."}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 0, "content": "Here are the risks of single-source supplier dependency:"}	demo-session-1	{gateway,gemini-2.5-flash}	2026-02-17 02:58:04.107	2026-02-17 02:58:06.629
9053e204-083c-4287-97f2-f4a7db95934b	2026-02-17 02:58:06.704	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-02d7ea809be2"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "What are the top 5 clauses to review in a SaaS vendor contract?"}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 0, "content": "When reviewing a SaaS vendor contract, focusing"}	demo-session-5	{gateway,gemini-2.5-flash}	2026-02-17 02:58:06.704	2026-02-17 02:58:09.054
a94a9b87-bec2-40a3-a49a-380cb2422abd	2026-02-17 02:58:09.131	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-cb3afe32fea6"}	\N	bob@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "Calculate: Supplier A costs $50/unit for 10000 units + $5000 shipping. Supplier B costs $45/unit for 10000 units + $8000 shipping + $3000 setup. Which is cheaper?"}], "temperature": 0.5}	{"model": "gemini-2.0-flash-001", "tokens": 0, "content": "Let's calculate the total cost for each supplier:\\n\\n**Supplier A:**\\n\\n*   Unit Cost: $50/unit * 10000 units = $500,000\\n*   Shipping: $5,000\\n*   Total Cost: $500,000 + $5,000 = $505,000\\n\\n**Supplier B:**\\n"}	demo-session-6	{gateway,gemini-2.0-flash-001}	2026-02-17 02:58:09.131	2026-02-17 02:58:11.257
ec7cf65b-2ad8-4796-89d2-77f2fe661560	2026-02-17 02:58:18.348	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-fa367d64d626"}	\N	test	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "Say hello"}], "temperature": 0.5}	{"model": "gemini-2.0-flash-001", "tokens": 0, "content": "Hello! How can I help you today?"}	\N	{gateway,gemini-2.0-flash-001}	2026-02-17 02:58:18.348	2026-02-17 02:58:19.026
8329819f-3a5f-4e80-b013-9f5a25c95b23	2026-02-17 03:00:34.668	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-8db033663229"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "What are 3 benefits of e-procurement systems?"}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 208, "content": "Here are 3 key"}	demo-fresh-1	{gateway,gemini-2.5-flash}	2026-02-17 03:00:34.668	2026-02-17 03:00:37.223
ccd88631-9b11-4a6c-b901-c9aab368c7c3	2026-02-17 03:00:50.048	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-f3dbb7afcdee"}	\N	bob@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "Compare centralized vs decentralized procurement models in 3 sentences."}], "temperature": 0.4}	{"model": "gemini-2.0-flash-001", "tokens": 87, "content": "Centralized procurement leverages economies of scale and standardized processes for cost savings and better control, but can be less responsive to local needs. Decentralized procurement allows for gre"}	demo-fresh-2	{gateway,gemini-2.0-flash-001}	2026-02-17 03:00:50.048	2026-02-17 03:00:51.34
8dfc4eca-acb3-42a3-8d75-9d93fa1d35af	2026-02-17 03:00:51.384	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-8f42da175c9b"}	\N	carol@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "system", "content": "You are a procurement AI assistant."}, {"role": "user", "content": "Draft a 3-line RFQ summary for office supplies vendor selection."}], "temperature": 0.7}	{"model": "gemini-2.5-flash", "tokens": 240, "content": "Request for Quotation (RFQ) for the procurement of general office supplies. We seek competitive pricing, high-quality products, and reliable delivery from qualified vendors. Submit detailed proposals "}	demo-fresh-3	{gateway,gemini-2.5-flash}	2026-02-17 03:00:51.384	2026-02-17 03:00:53.363
d50acc87-08fd-430f-85f8-505f7a3a25fb	2026-02-17 03:00:53.404	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-c16568f0ac46"}	\N	dave@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.0-flash-001", "messages": [{"role": "user", "content": "List 5 red flags in a supplier audit report."}], "temperature": 0.3}	{"model": "gemini-2.0-flash-001", "tokens": 311, "content": "Here are 5 red flags that might appear in a supplier audit report, indicating potential problems and requiring further investigation:\\n\\n1.  **Consistent Non-Compliance with Critical Requirements:** Thi"}	demo-fresh-4	{gateway,gemini-2.0-flash-001}	2026-02-17 03:00:53.404	2026-02-17 03:00:56.674
c7cb16dc-cb14-4b13-a2d4-6c97ed1078b4	2026-02-17 03:00:56.716	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-c76f4eaf6103"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "What is tail spend and why does it matter for procurement teams?"}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 209, "content": "**Tail spend**"}	demo-fresh-1	{gateway,gemini-2.5-flash}	2026-02-17 03:00:56.716	2026-02-17 03:00:58.888
d86ad628-6767-4032-b8b5-72e061daead3	2026-02-17 03:05:22.872	gateway-completion	proj-jai	{"agent_id": "", "tenant_id": "tenant-default", "request_id": "chatcmpl-28a6d07cf6c5"}	\N	alice@jaggaer.com	\N	\N	f	f	{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Explain maverick spending in procurement in one sentence."}], "temperature": 0.5}	{"model": "gemini-2.5-flash", "tokens": 106, "content": "Maverick spending in"}	demo-final	{gateway,gemini-2.5-flash}	2026-02-17 03:05:22.872	2026-02-17 03:05:24.621
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, name, email, email_verified, password, image, created_at, updated_at, feature_flags, admin) FROM stdin;
\.


--
-- Data for Name: verification_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.verification_tokens (identifier, token, expires) FROM stdin;
\.


--
-- Name: Account Account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."Account"
    ADD CONSTRAINT "Account_pkey" PRIMARY KEY (id);


--
-- Name: Session Session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."Session"
    ADD CONSTRAINT "Session_pkey" PRIMARY KEY (id);


--
-- Name: _prisma_migrations _prisma_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public._prisma_migrations
    ADD CONSTRAINT _prisma_migrations_pkey PRIMARY KEY (id);


--
-- Name: annotation_queue_items annotation_queue_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queue_items
    ADD CONSTRAINT annotation_queue_items_pkey PRIMARY KEY (id);


--
-- Name: annotation_queues annotation_queues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queues
    ADD CONSTRAINT annotation_queues_pkey PRIMARY KEY (id);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: background_migrations background_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.background_migrations
    ADD CONSTRAINT background_migrations_pkey PRIMARY KEY (id);


--
-- Name: batch_exports batch_exports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_exports
    ADD CONSTRAINT batch_exports_pkey PRIMARY KEY (id);


--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: cron_jobs cron_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cron_jobs
    ADD CONSTRAINT cron_jobs_pkey PRIMARY KEY (name);


--
-- Name: dataset_items dataset_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_items
    ADD CONSTRAINT dataset_items_pkey PRIMARY KEY (id, project_id);


--
-- Name: dataset_run_items dataset_run_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_run_items
    ADD CONSTRAINT dataset_run_items_pkey PRIMARY KEY (id, project_id);


--
-- Name: dataset_runs dataset_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_runs
    ADD CONSTRAINT dataset_runs_pkey PRIMARY KEY (id, project_id);


--
-- Name: datasets datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_pkey PRIMARY KEY (id, project_id);


--
-- Name: eval_templates eval_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_templates
    ADD CONSTRAINT eval_templates_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: job_configurations job_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_configurations
    ADD CONSTRAINT job_configurations_pkey PRIMARY KEY (id);


--
-- Name: job_executions job_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_executions
    ADD CONSTRAINT job_executions_pkey PRIMARY KEY (id);


--
-- Name: llm_api_keys llm_api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_api_keys
    ADD CONSTRAINT llm_api_keys_pkey PRIMARY KEY (id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: membership_invitations membership_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_invitations
    ADD CONSTRAINT membership_invitations_pkey PRIMARY KEY (id);


--
-- Name: models models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);


--
-- Name: observation_media observation_media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation_media
    ADD CONSTRAINT observation_media_pkey PRIMARY KEY (id);


--
-- Name: observations observations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observations
    ADD CONSTRAINT observations_pkey PRIMARY KEY (id);


--
-- Name: organization_memberships organization_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: posthog_integrations posthog_integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posthog_integrations
    ADD CONSTRAINT posthog_integrations_pkey PRIMARY KEY (project_id);


--
-- Name: prices prices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices
    ADD CONSTRAINT prices_pkey PRIMARY KEY (id);


--
-- Name: project_memberships project_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_memberships
    ADD CONSTRAINT project_memberships_pkey PRIMARY KEY (project_id, user_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: prompts prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_pkey PRIMARY KEY (id);


--
-- Name: score_configs score_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_configs
    ADD CONSTRAINT score_configs_pkey PRIMARY KEY (id);


--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);


--
-- Name: sso_configs sso_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_configs
    ADD CONSTRAINT sso_configs_pkey PRIMARY KEY (domain);


--
-- Name: trace_media trace_media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_media
    ADD CONSTRAINT trace_media_pkey PRIMARY KEY (id);


--
-- Name: trace_sessions trace_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_sessions
    ADD CONSTRAINT trace_sessions_pkey PRIMARY KEY (id, project_id);


--
-- Name: traces traces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.traces
    ADD CONSTRAINT traces_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: Account_provider_providerAccountId_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "Account_provider_providerAccountId_key" ON public."Account" USING btree (provider, "providerAccountId");


--
-- Name: Account_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "Account_user_id_idx" ON public."Account" USING btree (user_id);


--
-- Name: Session_session_token_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "Session_session_token_key" ON public."Session" USING btree (session_token);


--
-- Name: annotation_queue_items_annotator_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queue_items_annotator_user_id_idx ON public.annotation_queue_items USING btree (annotator_user_id);


--
-- Name: annotation_queue_items_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queue_items_created_at_idx ON public.annotation_queue_items USING btree (created_at);


--
-- Name: annotation_queue_items_id_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queue_items_id_project_id_idx ON public.annotation_queue_items USING btree (id, project_id);


--
-- Name: annotation_queue_items_object_id_object_type_project_id_que_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queue_items_object_id_object_type_project_id_que_idx ON public.annotation_queue_items USING btree (object_id, object_type, project_id, queue_id);


--
-- Name: annotation_queue_items_project_id_queue_id_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queue_items_project_id_queue_id_status_idx ON public.annotation_queue_items USING btree (project_id, queue_id, status);


--
-- Name: annotation_queues_id_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queues_id_project_id_idx ON public.annotation_queues USING btree (id, project_id);


--
-- Name: annotation_queues_project_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX annotation_queues_project_id_created_at_idx ON public.annotation_queues USING btree (project_id, created_at);


--
-- Name: annotation_queues_project_id_name_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX annotation_queues_project_id_name_key ON public.annotation_queues USING btree (project_id, name);


--
-- Name: api_keys_fast_hashed_secret_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_keys_fast_hashed_secret_key_idx ON public.api_keys USING btree (fast_hashed_secret_key);


--
-- Name: api_keys_fast_hashed_secret_key_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_keys_fast_hashed_secret_key_key ON public.api_keys USING btree (fast_hashed_secret_key);


--
-- Name: api_keys_hashed_secret_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_keys_hashed_secret_key_idx ON public.api_keys USING btree (hashed_secret_key);


--
-- Name: api_keys_hashed_secret_key_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_keys_hashed_secret_key_key ON public.api_keys USING btree (hashed_secret_key);


--
-- Name: api_keys_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_keys_id_key ON public.api_keys USING btree (id);


--
-- Name: api_keys_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_keys_project_id_idx ON public.api_keys USING btree (project_id);


--
-- Name: api_keys_public_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_keys_public_key_idx ON public.api_keys USING btree (public_key);


--
-- Name: api_keys_public_key_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_keys_public_key_key ON public.api_keys USING btree (public_key);


--
-- Name: audit_logs_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_created_at_idx ON public.audit_logs USING btree (created_at);


--
-- Name: audit_logs_org_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_org_id_idx ON public.audit_logs USING btree (org_id);


--
-- Name: audit_logs_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_project_id_idx ON public.audit_logs USING btree (project_id);


--
-- Name: audit_logs_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_updated_at_idx ON public.audit_logs USING btree (updated_at);


--
-- Name: audit_logs_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_user_id_idx ON public.audit_logs USING btree (user_id);


--
-- Name: background_migrations_name_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX background_migrations_name_key ON public.background_migrations USING btree (name);


--
-- Name: batch_exports_project_id_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX batch_exports_project_id_user_id_idx ON public.batch_exports USING btree (project_id, user_id);


--
-- Name: batch_exports_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX batch_exports_status_idx ON public.batch_exports USING btree (status);


--
-- Name: comments_project_id_object_type_object_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX comments_project_id_object_type_object_id_idx ON public.comments USING btree (project_id, object_type, object_id);


--
-- Name: dataset_items_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_items_created_at_idx ON public.dataset_items USING btree (created_at);


--
-- Name: dataset_items_dataset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_items_dataset_id_idx ON public.dataset_items USING hash (dataset_id);


--
-- Name: dataset_items_source_observation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_items_source_observation_id_idx ON public.dataset_items USING hash (source_observation_id);


--
-- Name: dataset_items_source_trace_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_items_source_trace_id_idx ON public.dataset_items USING hash (source_trace_id);


--
-- Name: dataset_items_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_items_updated_at_idx ON public.dataset_items USING btree (updated_at);


--
-- Name: dataset_run_items_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_created_at_idx ON public.dataset_run_items USING btree (created_at);


--
-- Name: dataset_run_items_dataset_item_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_dataset_item_id_idx ON public.dataset_run_items USING hash (dataset_item_id);


--
-- Name: dataset_run_items_dataset_run_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_dataset_run_id_idx ON public.dataset_run_items USING hash (dataset_run_id);


--
-- Name: dataset_run_items_observation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_observation_id_idx ON public.dataset_run_items USING hash (observation_id);


--
-- Name: dataset_run_items_trace_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_trace_id_idx ON public.dataset_run_items USING btree (trace_id);


--
-- Name: dataset_run_items_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_run_items_updated_at_idx ON public.dataset_run_items USING btree (updated_at);


--
-- Name: dataset_runs_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_runs_created_at_idx ON public.dataset_runs USING btree (created_at);


--
-- Name: dataset_runs_dataset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_runs_dataset_id_idx ON public.dataset_runs USING hash (dataset_id);


--
-- Name: dataset_runs_dataset_id_project_id_name_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX dataset_runs_dataset_id_project_id_name_key ON public.dataset_runs USING btree (dataset_id, project_id, name);


--
-- Name: dataset_runs_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dataset_runs_updated_at_idx ON public.dataset_runs USING btree (updated_at);


--
-- Name: datasets_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX datasets_created_at_idx ON public.datasets USING btree (created_at);


--
-- Name: datasets_project_id_name_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX datasets_project_id_name_key ON public.datasets USING btree (project_id, name);


--
-- Name: datasets_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX datasets_updated_at_idx ON public.datasets USING btree (updated_at);


--
-- Name: eval_templates_project_id_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eval_templates_project_id_id_idx ON public.eval_templates USING btree (project_id, id);


--
-- Name: eval_templates_project_id_name_version_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX eval_templates_project_id_name_version_key ON public.eval_templates USING btree (project_id, name, version);


--
-- Name: events_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX events_project_id_idx ON public.events USING btree (project_id);


--
-- Name: job_configurations_project_id_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_configurations_project_id_id_idx ON public.job_configurations USING btree (project_id, id);


--
-- Name: job_executions_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_created_at_idx ON public.job_executions USING btree (created_at);


--
-- Name: job_executions_job_configuration_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_job_configuration_id_idx ON public.job_executions USING btree (job_configuration_id);


--
-- Name: job_executions_job_input_trace_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_job_input_trace_id_idx ON public.job_executions USING btree (job_input_trace_id);


--
-- Name: job_executions_job_output_score_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_job_output_score_id_idx ON public.job_executions USING btree (job_output_score_id);


--
-- Name: job_executions_project_id_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_project_id_id_idx ON public.job_executions USING btree (project_id, id);


--
-- Name: job_executions_project_id_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_project_id_status_idx ON public.job_executions USING btree (project_id, status);


--
-- Name: job_executions_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX job_executions_updated_at_idx ON public.job_executions USING btree (updated_at);


--
-- Name: llm_api_keys_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX llm_api_keys_id_key ON public.llm_api_keys USING btree (id);


--
-- Name: llm_api_keys_project_id_provider_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX llm_api_keys_project_id_provider_key ON public.llm_api_keys USING btree (project_id, provider);


--
-- Name: media_project_id_sha_256_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX media_project_id_sha_256_hash_key ON public.media USING btree (project_id, sha_256_hash);


--
-- Name: membership_invitations_email_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX membership_invitations_email_idx ON public.membership_invitations USING btree (email);


--
-- Name: membership_invitations_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX membership_invitations_id_key ON public.membership_invitations USING btree (id);


--
-- Name: membership_invitations_org_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX membership_invitations_org_id_idx ON public.membership_invitations USING btree (org_id);


--
-- Name: membership_invitations_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX membership_invitations_project_id_idx ON public.membership_invitations USING btree (project_id);


--
-- Name: models_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX models_model_name_idx ON public.models USING btree (model_name);


--
-- Name: models_project_id_model_name_start_date_unit_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX models_project_id_model_name_start_date_unit_key ON public.models USING btree (project_id, model_name, start_date, unit);


--
-- Name: observation_media_project_id_observation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observation_media_project_id_observation_id_idx ON public.observation_media USING btree (project_id, observation_id);


--
-- Name: observation_media_project_id_trace_id_observation_id_media__key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX observation_media_project_id_trace_id_observation_id_media__key ON public.observation_media USING btree (project_id, trace_id, observation_id, media_id, field);


--
-- Name: observations_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_created_at_idx ON public.observations USING btree (created_at);


--
-- Name: observations_id_project_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX observations_id_project_id_key ON public.observations USING btree (id, project_id);


--
-- Name: observations_internal_model_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_internal_model_idx ON public.observations USING btree (internal_model);


--
-- Name: observations_model_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_model_idx ON public.observations USING btree (model);


--
-- Name: observations_project_id_internal_model_start_time_unit_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_project_id_internal_model_start_time_unit_idx ON public.observations USING btree (project_id, internal_model, start_time, unit);


--
-- Name: observations_project_id_prompt_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_project_id_prompt_id_idx ON public.observations USING btree (project_id, prompt_id);


--
-- Name: observations_project_id_start_time_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_project_id_start_time_type_idx ON public.observations USING btree (project_id, start_time, type);


--
-- Name: observations_prompt_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_prompt_id_idx ON public.observations USING btree (prompt_id);


--
-- Name: observations_start_time_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_start_time_idx ON public.observations USING btree (start_time);


--
-- Name: observations_trace_id_project_id_start_time_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_trace_id_project_id_start_time_idx ON public.observations USING btree (trace_id, project_id, start_time);


--
-- Name: observations_trace_id_project_id_type_start_time_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_trace_id_project_id_type_start_time_idx ON public.observations USING btree (trace_id, project_id, type, start_time);


--
-- Name: observations_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX observations_type_idx ON public.observations USING btree (type);


--
-- Name: organization_memberships_org_id_user_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX organization_memberships_org_id_user_id_key ON public.organization_memberships USING btree (org_id, user_id);


--
-- Name: organization_memberships_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_memberships_user_id_idx ON public.organization_memberships USING btree (user_id);


--
-- Name: prices_model_id_usage_type_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX prices_model_id_usage_type_key ON public.prices USING btree (model_id, usage_type);


--
-- Name: project_memberships_org_membership_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX project_memberships_org_membership_id_idx ON public.project_memberships USING btree (org_membership_id);


--
-- Name: project_memberships_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX project_memberships_project_id_idx ON public.project_memberships USING btree (project_id);


--
-- Name: project_memberships_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX project_memberships_user_id_idx ON public.project_memberships USING btree (user_id);


--
-- Name: projects_org_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX projects_org_id_idx ON public.projects USING btree (org_id);


--
-- Name: prompts_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX prompts_created_at_idx ON public.prompts USING btree (created_at);


--
-- Name: prompts_project_id_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX prompts_project_id_id_idx ON public.prompts USING btree (project_id, id);


--
-- Name: prompts_project_id_name_version_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX prompts_project_id_name_version_key ON public.prompts USING btree (project_id, name, version);


--
-- Name: prompts_tags_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX prompts_tags_idx ON public.prompts USING gin (tags);


--
-- Name: prompts_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX prompts_updated_at_idx ON public.prompts USING btree (updated_at);


--
-- Name: score_configs_categories_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_categories_idx ON public.score_configs USING btree (categories);


--
-- Name: score_configs_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_created_at_idx ON public.score_configs USING btree (created_at);


--
-- Name: score_configs_data_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_data_type_idx ON public.score_configs USING btree (data_type);


--
-- Name: score_configs_id_project_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX score_configs_id_project_id_key ON public.score_configs USING btree (id, project_id);


--
-- Name: score_configs_is_archived_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_is_archived_idx ON public.score_configs USING btree (is_archived);


--
-- Name: score_configs_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_project_id_idx ON public.score_configs USING btree (project_id);


--
-- Name: score_configs_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX score_configs_updated_at_idx ON public.score_configs USING btree (updated_at);


--
-- Name: scores_author_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_author_user_id_idx ON public.scores USING btree (author_user_id);


--
-- Name: scores_config_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_config_id_idx ON public.scores USING btree (config_id);


--
-- Name: scores_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_created_at_idx ON public.scores USING btree (created_at);


--
-- Name: scores_id_project_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX scores_id_project_id_key ON public.scores USING btree (id, project_id);


--
-- Name: scores_observation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_observation_id_idx ON public.scores USING hash (observation_id);


--
-- Name: scores_project_id_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_project_id_name_idx ON public.scores USING btree (project_id, name);


--
-- Name: scores_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_source_idx ON public.scores USING btree (source);


--
-- Name: scores_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_timestamp_idx ON public.scores USING btree ("timestamp");


--
-- Name: scores_trace_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_trace_id_idx ON public.scores USING hash (trace_id);


--
-- Name: scores_value_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_value_idx ON public.scores USING btree (value);


--
-- Name: trace_media_project_id_trace_id_media_id_field_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX trace_media_project_id_trace_id_media_id_field_key ON public.trace_media USING btree (project_id, trace_id, media_id, field);


--
-- Name: trace_sessions_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX trace_sessions_created_at_idx ON public.trace_sessions USING btree (created_at);


--
-- Name: trace_sessions_project_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX trace_sessions_project_id_idx ON public.trace_sessions USING btree (project_id);


--
-- Name: trace_sessions_updated_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX trace_sessions_updated_at_idx ON public.trace_sessions USING btree (updated_at);


--
-- Name: traces_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_created_at_idx ON public.traces USING btree (created_at);


--
-- Name: traces_id_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_id_user_id_idx ON public.traces USING btree (id, user_id);


--
-- Name: traces_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_name_idx ON public.traces USING btree (name);


--
-- Name: traces_project_id_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_project_id_timestamp_idx ON public.traces USING btree (project_id, "timestamp");


--
-- Name: traces_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_session_id_idx ON public.traces USING btree (session_id);


--
-- Name: traces_tags_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_tags_idx ON public.traces USING gin (tags);


--
-- Name: traces_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_timestamp_idx ON public.traces USING btree ("timestamp");


--
-- Name: traces_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX traces_user_id_idx ON public.traces USING btree (user_id);


--
-- Name: users_email_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);


--
-- Name: verification_tokens_identifier_token_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX verification_tokens_identifier_token_key ON public.verification_tokens USING btree (identifier, token);


--
-- Name: verification_tokens_token_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX verification_tokens_token_key ON public.verification_tokens USING btree (token);


--
-- Name: Account Account_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."Account"
    ADD CONSTRAINT "Account_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: Session Session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."Session"
    ADD CONSTRAINT "Session_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: annotation_queue_items annotation_queue_items_annotator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queue_items
    ADD CONSTRAINT annotation_queue_items_annotator_user_id_fkey FOREIGN KEY (annotator_user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: annotation_queue_items annotation_queue_items_locked_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queue_items
    ADD CONSTRAINT annotation_queue_items_locked_by_user_id_fkey FOREIGN KEY (locked_by_user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: annotation_queue_items annotation_queue_items_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queue_items
    ADD CONSTRAINT annotation_queue_items_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: annotation_queue_items annotation_queue_items_queue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queue_items
    ADD CONSTRAINT annotation_queue_items_queue_id_fkey FOREIGN KEY (queue_id) REFERENCES public.annotation_queues(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: annotation_queues annotation_queues_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_queues
    ADD CONSTRAINT annotation_queues_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: api_keys api_keys_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: batch_exports batch_exports_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_exports
    ADD CONSTRAINT batch_exports_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: comments comments_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dataset_items dataset_items_dataset_id_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_items
    ADD CONSTRAINT dataset_items_dataset_id_project_id_fkey FOREIGN KEY (dataset_id, project_id) REFERENCES public.datasets(id, project_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dataset_run_items dataset_run_items_dataset_item_id_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_run_items
    ADD CONSTRAINT dataset_run_items_dataset_item_id_project_id_fkey FOREIGN KEY (dataset_item_id, project_id) REFERENCES public.dataset_items(id, project_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dataset_run_items dataset_run_items_dataset_run_id_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_run_items
    ADD CONSTRAINT dataset_run_items_dataset_run_id_project_id_fkey FOREIGN KEY (dataset_run_id, project_id) REFERENCES public.dataset_runs(id, project_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dataset_runs dataset_runs_dataset_id_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_runs
    ADD CONSTRAINT dataset_runs_dataset_id_project_id_fkey FOREIGN KEY (dataset_id, project_id) REFERENCES public.datasets(id, project_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: datasets datasets_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: eval_templates eval_templates_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_templates
    ADD CONSTRAINT eval_templates_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: events events_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: job_configurations job_configurations_eval_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_configurations
    ADD CONSTRAINT job_configurations_eval_template_id_fkey FOREIGN KEY (eval_template_id) REFERENCES public.eval_templates(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: job_configurations job_configurations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_configurations
    ADD CONSTRAINT job_configurations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: job_executions job_executions_job_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_executions
    ADD CONSTRAINT job_executions_job_configuration_id_fkey FOREIGN KEY (job_configuration_id) REFERENCES public.job_configurations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: job_executions job_executions_job_output_score_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_executions
    ADD CONSTRAINT job_executions_job_output_score_id_fkey FOREIGN KEY (job_output_score_id) REFERENCES public.scores(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: job_executions job_executions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_executions
    ADD CONSTRAINT job_executions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: llm_api_keys llm_api_keys_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_api_keys
    ADD CONSTRAINT llm_api_keys_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: media media_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: membership_invitations membership_invitations_invited_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_invitations
    ADD CONSTRAINT membership_invitations_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: membership_invitations membership_invitations_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_invitations
    ADD CONSTRAINT membership_invitations_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: membership_invitations membership_invitations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_invitations
    ADD CONSTRAINT membership_invitations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: models models_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: observation_media observation_media_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation_media
    ADD CONSTRAINT observation_media_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: observation_media observation_media_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation_media
    ADD CONSTRAINT observation_media_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: observations observations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observations
    ADD CONSTRAINT observations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: organization_memberships organization_memberships_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: organization_memberships organization_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: posthog_integrations posthog_integrations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posthog_integrations
    ADD CONSTRAINT posthog_integrations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: prices prices_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices
    ADD CONSTRAINT prices_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.models(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: project_memberships project_memberships_org_membership_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_memberships
    ADD CONSTRAINT project_memberships_org_membership_id_fkey FOREIGN KEY (org_membership_id) REFERENCES public.organization_memberships(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: project_memberships project_memberships_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_memberships
    ADD CONSTRAINT project_memberships_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: project_memberships project_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_memberships
    ADD CONSTRAINT project_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: projects projects_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: prompts prompts_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: score_configs score_configs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_configs
    ADD CONSTRAINT score_configs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: scores scores_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.score_configs(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: scores scores_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: trace_media trace_media_media_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_media
    ADD CONSTRAINT trace_media_media_id_fkey FOREIGN KEY (media_id) REFERENCES public.media(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: trace_media trace_media_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_media
    ADD CONSTRAINT trace_media_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: trace_sessions trace_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_sessions
    ADD CONSTRAINT trace_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: traces traces_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.traces
    ADD CONSTRAINT traces_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: traces traces_session_id_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.traces
    ADD CONSTRAINT traces_session_id_project_id_fkey FOREIGN KEY (session_id, project_id) REFERENCES public.trace_sessions(id, project_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict 4ubirsawhg1gqnrDlgbZEmBalhzPq1I6YAFxKAvF5LuCoKKzMIOXFmwho4kwCyO

