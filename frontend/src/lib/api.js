const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export async function fetchGraphStats() {
	const r = await fetch(`${BASE}/graph/stats`);
	return r.json();
}

export async function fetchFullGraph() {
	const r = await fetch(`${BASE}/graph`);
	return r.json();
}

export async function fetchNode(nodeId) {
	const r = await fetch(`${BASE}/graph/node/${encodeURIComponent(nodeId)}`);
	if (!r.ok) return null;
	return r.json();
}

export async function fetchNeighbours(nodeId, depth = 1) {
	const r = await fetch(
		`${BASE}/graph/neighbours/${encodeURIComponent(nodeId)}?depth=${depth}`,
	);
	return r.json();
}

export async function fetchFlow(nodeId) {
	const r = await fetch(`${BASE}/graph/flow/${encodeURIComponent(nodeId)}`);
	return r.json();
}

export async function sendQuery(message) {
	const r = await fetch(`${BASE}/query`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ message }),
	});
	return r.json();
}
