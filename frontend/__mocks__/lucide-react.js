// Auto-mock for lucide-react — returns a simple span for every icon
const handler = {
  get(_, name) {
    if (name === "__esModule") return true;
    if (name === "default") return handler;
    // Return a functional React component for each icon name
    const Component = ({ size, className, ...rest }) => {
      const React = require("react");
      return React.createElement("span", {
        "data-testid": `icon-${name}`,
        "data-lucide": name,
        className,
        ...rest,
      });
    };
    Component.displayName = name;
    return Component;
  },
};

module.exports = new Proxy({}, handler);
