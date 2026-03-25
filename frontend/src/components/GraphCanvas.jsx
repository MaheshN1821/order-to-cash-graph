import React, { useEffect, useRef } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { NodeBorderProgram } from "@sigma/node-border";
import forceAtlas2 from "graphology-layout-forceatlas2";
import { buildGraphologyGraph, TYPE_COLOR } from "../lib/graphUtils";
import { fetchNode } from "../lib/api";

export default function GraphCanvas({
	graphData,
	onNodeSelect,
	highlightIds,
	filterType,
}) {
	const containerRef = useRef(null);
	const sigmaRef = useRef(null);
	const graphRef = useRef(null);

	useEffect(() => {
		if (!containerRef.current || !graphData) return;

		if (sigmaRef.current) {
			sigmaRef.current.kill();
			sigmaRef.current = null;
		}

		const graph = buildGraphologyGraph(graphData);
		graphRef.current = graph;

		try {
			forceAtlas2.assign(graph, {
				iterations: 300,
				settings: {
					gravity: 0.001, // very low — stops centre-pull collapsing the graph
					scalingRatio: 99, // high — pushes nodes apart (main spread control)
					strongGravityMode: false,
					linLogMode: false, // linear mode keeps distant nodes further out
					barnesHutOptimize: true, // faster on 600+ nodes
					barnesHutTheta: 0.5,
					slowDown: 5, // more iterations to settle without overshooting
					edgeWeightInfluence: 0,
				},
			});
		} catch (e) {}

		const renderer = new Sigma(graph, containerRef.current, {
			renderEdgeLabels: false,
			defaultEdgeColor: "#d1d5db",
			labelFont: "Syne, sans-serif",
			labelSize: 11,
			labelWeight: "500",
			labelColor: { color: "#374151" },
			minCameraRatio: 0.05,
			maxCameraRatio: 4,
			defaultNodeType: "border",
			nodeProgramClasses: { border: NodeBorderProgram },
		});

		sigmaRef.current = renderer;

		renderer.on("clickNode", async ({ node }) => {
			containerRef.current.style.cursor = "wait";
			try {
				const nodeData = await fetchNode(node);
				const graphAttrs = graph.getNodeAttributes(node);
				onNodeSelect({
					id: node,
					...(nodeData || {}),
					meta: nodeData || graphAttrs.meta,
					entity_type: graphAttrs.entity_type,
					label: graphAttrs.label,
				});
			} catch (e) {
				const graphAttrs = graph.getNodeAttributes(node);
				onNodeSelect({ id: node, ...graphAttrs.meta, meta: graphAttrs.meta });
			} finally {
				containerRef.current.style.cursor = "pointer";
			}
		});

		renderer.on("enterNode", () => {
			containerRef.current.style.cursor = "pointer";
		});
		renderer.on("leaveNode", () => {
			containerRef.current.style.cursor = "default";
		});
		renderer.on("clickStage", () => {
			onNodeSelect(null);
		});

		return () => {
			renderer.kill();
			sigmaRef.current = null;
		};
	}, [graphData]);

	// Re-apply colours whenever highlight or filter changes
	useEffect(() => {
		if (!graphRef.current || !sigmaRef.current) return;
		const graph = graphRef.current;

		graph.forEachNode((node, attrs) => {
			const color = TYPE_COLOR[attrs.entity_type] || "#94a3b8";
			const isWrongType = filterType && attrs.entity_type !== filterType;
			const isDimmed =
				(highlightIds && highlightIds.size > 0 && !highlightIds.has(node)) ||
				isWrongType;

			// borderColor  = the ring colour
			// color        = interior fill (white when outlined style)
			graph.setNodeAttribute(node, "borderColor", isDimmed ? "#e5e7eb" : color);
			graph.setNodeAttribute(node, "color", isDimmed ? "#f9fafb" : "#ffffff");
			graph.setNodeAttribute(
				node,
				"size",
				isDimmed
					? (attrs.baseSize || attrs.size) * 0.6
					: attrs.baseSize || attrs.size,
			);
		});

		graph.forEachEdge((edge, _attrs, src, tgt) => {
			const active =
				!highlightIds ||
				highlightIds.size === 0 ||
				(highlightIds.has(src) && highlightIds.has(tgt));
			const srcType = graph.getNodeAttribute(src, "entity_type");
			const tgtType = graph.getNodeAttribute(tgt, "entity_type");
			const typeMatch =
				!filterType || srcType === filterType || tgtType === filterType;
			graph.setEdgeAttribute(
				edge,
				"color",
				active && typeMatch ? "#a5b4fc" : "#f3f4f6",
			);
		});

		sigmaRef.current.refresh();
	}, [highlightIds, filterType]);

	return (
		<div
			ref={containerRef}
			style={{ width: "100%", height: "100%", background: "#f8fafc" }}
		/>
	);
}
