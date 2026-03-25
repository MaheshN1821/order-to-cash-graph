import React, { useState, useEffect, useCallback, useRef } from "react";
import GraphCanvas from "./components/GraphCanvas";
import NodePanel from "./components/NodePanel";
import ChatPanel from "./components/ChatPanel";
import Toolbar from "./components/Toolbar";
import {
	fetchFullGraph,
	fetchGraphStats,
	fetchNeighbours,
	fetchFlow,
} from "./lib/api";

export default function App() {
	const [graphData, setGraphData] = useState(null);
	const [stats, setStats] = useState(null);
	const [selectedNode, setSelectedNode] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [highlightIds, setHighlightIds] = useState(null);
	const [filterType, setFilterType] = useState(null); // ← new: entity type filter
	const graphDataRef = useRef(null);

	useEffect(() => {
		async function boot() {
			try {
				const [s, g] = await Promise.all([fetchGraphStats(), fetchFullGraph()]);
				setStats(s);
				setGraphData(g);
				graphDataRef.current = g;
			} catch {
				setError("Cannot connect to backend.");
			} finally {
				setLoading(false);
			}
		}
		boot();
	}, []);

	const handleExpand = useCallback(async (nodeId) => {
		try {
			const sub = await fetchNeighbours(nodeId, 1);
			if (!graphDataRef.current) return;
			const existing = graphDataRef.current;
			const nodeIds = new Set(existing.nodes.map((n) => n.id));
			const edgeKeys = new Set(
				existing.edges.map((e) => `${e.source}--${e.target}`),
			);
			const merged = {
				nodes: [
					...existing.nodes,
					...sub.nodes.filter((n) => !nodeIds.has(n.id)),
				],
				edges: [
					...existing.edges,
					...sub.edges.filter((e) => !edgeKeys.has(`${e.source}--${e.target}`)),
				],
			};
			graphDataRef.current = merged;
			setGraphData({ ...merged });
		} catch (e) {
			console.error("Expand failed", e);
		}
	}, []);

	const handleTraceFlow = useCallback(async (nodeId) => {
		try {
			const flow = await fetchFlow(nodeId);
			setHighlightIds(new Set(flow.nodes.map((n) => n.id)));
			setFilterType(null);
			const existing = graphDataRef.current;
			const nodeIds = new Set(existing.nodes.map((n) => n.id));
			const edgeKeys = new Set(
				existing.edges.map((e) => `${e.source}--${e.target}`),
			);
			const merged = {
				nodes: [
					...existing.nodes,
					...flow.nodes.filter((n) => !nodeIds.has(n.id)),
				],
				edges: [
					...existing.edges,
					...flow.edges.filter(
						(e) => !edgeKeys.has(`${e.source}--${e.target}`),
					),
				],
			};
			graphDataRef.current = merged;
			setGraphData({ ...merged });
		} catch (e) {
			console.error("Trace flow failed", e);
		}
	}, []);

	const handleReset = useCallback(() => {
		setHighlightIds(null);
		setFilterType(null);
		setSelectedNode(null);
	}, []);

	// When a legend tag is clicked — clear highlights, set type filter
	const handleFilterType = useCallback((type) => {
		setFilterType(type);
		setHighlightIds(null); // clear any existing highlight so they don't conflict
	}, []);

	const handleQueryResults = useCallback((results) => {
		const idFields = [
			"sales_order",
			"billing_document",
			"delivery_document",
			"business_partner",
			"product",
			"accounting_document",
		];
		const ids = new Set();
		results.forEach((row) => {
			idFields.forEach((field) => {
				if (row[field]) {
					[
						"sales_order",
						"billing_doc",
						"delivery",
						"customer",
						"product",
						"journal_entry",
						"payment",
					].forEach((p) => ids.add(`${p}:${row[field]}`));
				}
			});
		});
		if (ids.size > 0) {
			setHighlightIds(ids);
			setFilterType(null);
		}
	}, []);

	if (loading)
		return (
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					height: "100vh",
					flexDirection: "column",
					gap: 14,
					background: "#f8fafc",
				}}
			>
				<style>{`@keyframes breathe{0%,100%{opacity:.4;transform:scale(.9)}50%{opacity:1;transform:scale(1.05)}}`}</style>
				<div
					style={{
						width: 44,
						height: 44,
						borderRadius: 11,
						background: "#4f46e5",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 18,
						fontWeight: 700,
						color: "#fff",
						animation: "breathe 1.5s ease-in-out infinite",
					}}
				>
					G
				</div>
				<div
					style={{
						color: "#9ca3af",
						fontSize: 13,
						fontFamily: "IBM Plex Mono, monospace",
					}}
				>
					Loading graph…
				</div>
			</div>
		);

	if (error)
		return (
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					height: "100vh",
					flexDirection: "column",
					gap: 10,
					background: "#f8fafc",
				}}
			>
				<div style={{ color: "#d97706", fontSize: 14 }}>{error}</div>
				<div
					style={{
						color: "#9ca3af",
						fontSize: 12,
						fontFamily: "IBM Plex Mono, monospace",
					}}
				>
					Try again later!
				</div>
			</div>
		);

	return (
		<div
			style={{
				display: "flex",
				height: "100vh",
				overflow: "hidden",
				background: "#f8fafc",
			}}
		>
			{/* Left — graph */}
			<div style={{ flex: 1, position: "relative", minWidth: 0 }}>
				<Toolbar
					stats={stats}
					onReset={handleReset}
					filterType={filterType}
					onFilterType={handleFilterType}
				/>

				<div
					style={{
						position: "absolute",
						top: 48,
						left: 0,
						right: 0,
						bottom: 0,
					}}
				>
					<GraphCanvas
						graphData={graphData}
						onNodeSelect={setSelectedNode}
						highlightIds={highlightIds}
						filterType={filterType}
					/>

					{selectedNode && (
						<NodePanel
							node={selectedNode}
							onClose={() => setSelectedNode(null)}
							onExpand={handleExpand}
							onTraceFlow={handleTraceFlow}
						/>
					)}

					{!selectedNode && (
						<div
							style={{
								position: "absolute",
								bottom: 16,
								left: 16,
								fontSize: 11,
								color: "#9ca3af",
								fontFamily: "IBM Plex Mono, monospace",
								background: "rgba(255,255,255,0.9)",
								padding: "5px 10px",
								borderRadius: 8,
								border: "1px solid #e5e7eb",
							}}
						>
							Click any node to inspect · Click legend tags to filter · Scroll
							to zoom
						</div>
					)}
				</div>
			</div>

			{/* Right — chat */}
			<div style={{ width: 360, flexShrink: 0 }}>
				<ChatPanel onQueryResults={handleQueryResults} />
			</div>
		</div>
	);
}
