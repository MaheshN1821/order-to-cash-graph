import Graph from "graphology";

export const TYPE_COLOR = {
	customer: "#6366f1",
	product: "#0d9488",
	plant: "#94a3b8",
	sales_order: "#3b82f6",
	delivery: "#f59e0b",
	billing_doc: "#f97316",
	journal_entry: "#ec4899",
	payment: "#22c55e",
};

export const TYPE_SIZE = {
	customer: 22,
	sales_order: 17,
	delivery: 15,
	billing_doc: 15,
	journal_entry: 13,
	payment: 13,
	product: 11,
	plant: 11,
};

export const TYPE_LABEL = {
	customer: "Customer",
	product: "Product",
	plant: "Plant",
	sales_order: "Sales Order",
	delivery: "Delivery",
	billing_doc: "Billing Doc",
	journal_entry: "Journal Entry",
	payment: "Payment",
};

export function buildGraphologyGraph(data) {
	const graph = new Graph({ multi: false, type: "directed" });

	data.nodes.forEach((node) => {
		const color = TYPE_COLOR[node.entity_type] || "#94a3b8";
		const size = TYPE_SIZE[node.entity_type] || 11;
		graph.addNode(node.id, {
			label: node.label,
			entity_type: node.entity_type,
			// NodeBorderProgram uses `color` for fill and `borderColor` for the ring
			color: "#ffffff", // white interior
			borderColor: color, // coloured border
			baseSize: size,
			size,
			x: Math.random() * 1000 - 500,
			y: Math.random() * 1000 - 500,
			meta: node,
		});
	});

	data.edges.forEach((edge, i) => {
		if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
			if (!graph.hasEdge(edge.source, edge.target)) {
				graph.addEdgeWithKey(
					`${edge.source}--${edge.target}--${i}`,
					edge.source,
					edge.target,
					{
						relationship: edge.relationship || "",
						color: "#d1d5db",
						size: 1.2,
					},
				);
			}
		}
	});

	return graph;
}

export function formatMetaValue(key, val) {
	if (val === null || val === undefined) return "—";
	if (typeof val === "boolean") return val ? "Yes" : "No";
	if (typeof val === "number") {
		if (key.includes("amount") || key.includes("value"))
			return new Intl.NumberFormat("en-IN", {
				maximumFractionDigits: 2,
			}).format(val);
		return String(val);
	}
	if (typeof val === "object") return JSON.stringify(val);
	return String(val);
}

export const HIDDEN_META_KEYS = new Set([
	"id",
	"label",
	"color",
	"shape",
	"entity_id",
	"entity_type",
	"predecessors",
	"successors",
	"in_degree",
	"out_degree",
]);

