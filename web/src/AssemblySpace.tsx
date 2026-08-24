import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import "./assembly-space.css";

export interface AssemblyNode {
  id: string;
  label: string;
  kind: string;
  depth: number;
  value?: number;
  unit?: string;
  epistemicClass?: string;
}

export interface AssemblyEdge {
  src: string;
  dst: string;
  relation: string;
}

export interface AssemblySpaceProps {
  nodes: AssemblyNode[];
  edges?: AssemblyEdge[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  title?: string;
}

interface Point {
  x: number;
  y: number;
}

interface LayoutPoint extends Point {
  width: number;
}

interface LayoutResult {
  positions: Map<string, LayoutPoint>;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface NodeVisual {
  group: THREE.Group;
  body: THREE.Mesh<THREE.BoxGeometry, THREE.MeshBasicMaterial>;
  outline: THREE.LineSegments<THREE.EdgesGeometry, THREE.LineBasicMaterial>;
  accent: THREE.Mesh<THREE.BoxGeometry, THREE.MeshBasicMaterial>;
  label: THREE.Sprite;
  baseColor: number;
}

interface EdgeVisual {
  line: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>;
  arrow: THREE.Mesh<THREE.ConeGeometry, THREE.MeshBasicMaterial>;
  baseColor: number;
}

interface GraphVisuals {
  root: THREE.Group;
  nodeVisuals: Map<string, NodeVisual>;
  edgeVisuals: Array<{ edge: AssemblyEdge; visual: EdgeVisual }>;
}

interface ViewState {
  zoom: number;
  panX: number;
  panY: number;
}

interface PointerState {
  id: number;
  x: number;
  y: number;
  lastX: number;
  lastY: number;
  moved: boolean;
}

const SCHEMATIC_ORANGE = 0xff7345;
const SCHEMATIC_CYAN = 0x5cc8dc;
const SCHEMATIC_GRID = 0x1a2b31;
const MAX_DPR = 2;

const KIND_PALETTE = [
  0xff7345,
  0x5cc8dc,
  0xd59bff,
  0xffc36a,
  0x65d89b,
  0xe587a7,
  0x93a8ff,
];

function usePrefersReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return undefined;
    }

    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener?.("change", update);

    return () => query.removeEventListener?.("change", update);
  }, []);

  return reducedMotion;
}

function colorForKind(kind: string): number {
  let hash = 0;
  for (let index = 0; index < kind.length; index += 1) {
    hash = (hash * 31 + kind.charCodeAt(index)) | 0;
  }
  return KIND_PALETTE[Math.abs(hash) % KIND_PALETTE.length];
}

function colorWithAlpha(color: number, amount: number): number {
  const red = Math.round(((color >> 16) & 0xff) * amount);
  const green = Math.round(((color >> 8) & 0xff) * amount);
  const blue = Math.round((color & 0xff) * amount);
  return (red << 16) | (green << 8) | blue;
}

function visualWidthFor(label: string): number {
  return Math.min(4.7, Math.max(3.15, 2.45 + label.length * 0.065));
}

function createLayout(nodes: AssemblyNode[]): LayoutResult {
  const positions = new Map<string, LayoutPoint>();
  const buckets = new Map<number, Array<{ node: AssemblyNode; index: number }>>();

  nodes.forEach((node, index) => {
    const depth = Number.isFinite(node.depth) ? node.depth : 0;
    const bucket = buckets.get(depth) ?? [];
    bucket.push({ node, index });
    buckets.set(depth, bucket);
  });

  const depths = [...buckets.keys()].sort((a, b) => a - b);
  const minDepth = depths[0] ?? 0;
  const maxDepth = depths[depths.length - 1] ?? minDepth;
  const xSpan = Math.max(0, maxDepth - minDepth) * 4.2;
  const xOrigin = -xSpan / 2;
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  depths.forEach((depth) => {
    const bucket = buckets.get(depth) ?? [];
    bucket.forEach(({ node }, bucketIndex) => {
      const x = xOrigin + (depth - minDepth) * 4.2;
      const y = (bucket.length - 1) * 1.35 / 2 - bucketIndex * 1.35;
      const width = visualWidthFor(node.label);
      positions.set(node.id, { x, y, width });
      minX = Math.min(minX, x - width / 2);
      maxX = Math.max(maxX, x + width / 2);
      minY = Math.min(minY, y - 0.72);
      maxY = Math.max(maxY, y + 0.72);
    });
  });

  if (!Number.isFinite(minX)) {
    return { positions, minX: -4, maxX: 4, minY: -3, maxY: 3 };
  }

  return { positions, minX, maxX, minY, maxY };
}

function roundedRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
): void {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + safeRadius, y);
  context.lineTo(x + width - safeRadius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  context.lineTo(x + width, y + height - safeRadius);
  context.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  context.lineTo(x + safeRadius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  context.lineTo(x, y + safeRadius);
  context.quadraticCurveTo(x, y, x + safeRadius, y);
  context.closePath();
}

function truncateLabel(value: string, maxCharacters: number): string {
  if (value.length <= maxCharacters) {
    return value;
  }
  return `${value.slice(0, Math.max(1, maxCharacters - 1))}…`;
}

function createLabelTexture(node: AssemblyNode, color: number): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 112;
  const context = canvas.getContext("2d");

  if (!context) {
    return new THREE.CanvasTexture(canvas);
  }

  const colorHex = `#${color.toString(16).padStart(6, "0")}`;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(8, 14, 17, 0.94)";
  roundedRect(context, 2, 2, canvas.width - 4, canvas.height - 4, 14);
  context.fill();
  context.strokeStyle = colorHex;
  context.lineWidth = 3;
  roundedRect(context, 2, 2, canvas.width - 4, canvas.height - 4, 14);
  context.stroke();

  context.fillStyle = colorHex;
  roundedRect(context, 14, 16, 8, canvas.height - 32, 4);
  context.fill();

  context.font = "600 25px Segoe UI, Arial, sans-serif";
  context.fillStyle = "#eaf2f2";
  context.textBaseline = "middle";
  context.fillText(truncateLabel(node.label || node.id, 31), 38, 41);
  context.font = "500 16px Cascadia Mono, Consolas, monospace";
  context.fillStyle = "#8fa4a8";
  context.fillText(truncateLabel(node.kind || "—", 40), 38, 80);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function disposeMaterial(material: THREE.Material): void {
  const materialWithMap = material as THREE.Material & { map?: THREE.Texture | null };
  materialWithMap.map?.dispose();
  material.dispose();
}

function disposeObject(root: THREE.Object3D): void {
  root.traverse((child) => {
    const disposable = child as THREE.Object3D & {
      geometry?: THREE.BufferGeometry;
      material?: THREE.Material | THREE.Material[];
    };
    disposable.geometry?.dispose();
    if (Array.isArray(disposable.material)) {
      disposable.material.forEach(disposeMaterial);
    } else if (disposable.material) {
      disposeMaterial(disposable.material);
    }
  });
}

function makeGrid(bounds: LayoutResult): THREE.LineSegments {
  const padding = 5;
  const minX = Math.floor((bounds.minX - padding) / 2) * 2;
  const maxX = Math.ceil((bounds.maxX + padding) / 2) * 2;
  const minY = Math.floor((bounds.minY - padding) / 2) * 2;
  const maxY = Math.ceil((bounds.maxY + padding) / 2) * 2;
  const positions: number[] = [];

  for (let x = minX; x <= maxX; x += 2) {
    positions.push(x, minY, -0.5, x, maxY, -0.5);
  }
  for (let y = minY; y <= maxY; y += 2) {
    positions.push(minX, y, -0.5, maxX, y, -0.5);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  const material = new THREE.LineBasicMaterial({
    color: SCHEMATIC_GRID,
    transparent: true,
    opacity: 0.7,
  });
  return new THREE.LineSegments(geometry, material);
}

function makeNodeVisual(node: AssemblyNode, position: LayoutPoint): NodeVisual {
  const baseColor = colorForKind(node.kind);
  const bodyGeometry = new THREE.BoxGeometry(position.width, 0.9, 0.3);
  const bodyMaterial = new THREE.MeshBasicMaterial({
    color: colorWithAlpha(baseColor, 0.26),
    transparent: true,
    opacity: 0.95,
  });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);

  const outline = new THREE.LineSegments(
    new THREE.EdgesGeometry(bodyGeometry),
    new THREE.LineBasicMaterial({ color: baseColor, transparent: true, opacity: 0.9 }),
  );

  const accent = new THREE.Mesh(
    new THREE.BoxGeometry(0.12, 0.56, 0.34),
    new THREE.MeshBasicMaterial({ color: baseColor }),
  );
  accent.position.set(-position.width / 2 + 0.24, 0, 0.03);

  const labelTexture = createLabelTexture(node, baseColor);
  const labelMaterial = new THREE.SpriteMaterial({
    map: labelTexture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const label = new THREE.Sprite(labelMaterial);
  label.scale.set(position.width, 0.78, 1);
  label.position.set(0, -0.98, 0.18);

  const group = new THREE.Group();
  group.position.set(position.x, position.y, 0);
  group.userData.nodeId = node.id;
  group.add(body, outline, accent, label);

  return { group, body, outline, accent, label, baseColor };
}

function makeEdgeVisual(
  edge: AssemblyEdge,
  source: Point,
  destination: Point,
): EdgeVisual {
  const sourcePoint = new THREE.Vector3(source.x, source.y, -0.08);
  const destinationPoint = new THREE.Vector3(destination.x, destination.y, -0.08);
  const direction = destinationPoint.clone().sub(sourcePoint);
  const length = direction.length();
  const unitDirection = length > 0.0001 ? direction.normalize() : new THREE.Vector3(1, 0, 0);
  const endInset = Math.min(0.6, Math.max(0.25, length * 0.18));
  const lineEnd = destinationPoint.clone().sub(unitDirection.clone().multiplyScalar(endInset));
  const lineStart = sourcePoint.clone().add(unitDirection.clone().multiplyScalar(endInset * 0.4));
  const lineGeometry = new THREE.BufferGeometry().setFromPoints([lineStart, lineEnd]);
  const baseColor = edge.relation ? SCHEMATIC_CYAN : 0x55767d;
  const line = new THREE.Line(
    lineGeometry,
    new THREE.LineBasicMaterial({ color: baseColor, transparent: true, opacity: 0.65 }),
  );

  const arrow = new THREE.Mesh(
    new THREE.ConeGeometry(0.1, 0.26, 4),
    new THREE.MeshBasicMaterial({ color: baseColor, transparent: true, opacity: 0.82 }),
  );
  const arrowPoint = destinationPoint.clone().sub(unitDirection.clone().multiplyScalar(0.45));
  arrow.position.copy(arrowPoint);
  arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), unitDirection);

  return { line, arrow, baseColor };
}

function formatValue(node: AssemblyNode): string | null {
  if (node.value === undefined) {
    return null;
  }
  const value = Number.isFinite(node.value) ? node.value.toLocaleString() : String(node.value);
  return node.unit ? `${value} ${node.unit}` : value;
}

export default function AssemblySpace({
  nodes,
  edges = [],
  selectedId,
  onSelect,
  title = "Assembly space",
}: AssemblySpaceProps) {
  const canvasHostRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const visualsRef = useRef<GraphVisuals | null>(null);
  const layoutRef = useRef<LayoutResult | null>(null);
  const rafRef = useRef<number | null>(null);
  const pointerRef = useRef<PointerState | null>(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const viewRef = useRef<ViewState>({ zoom: 1, panX: 0, panY: 0 });
  const selectedIdRef = useRef<string | null | undefined>(selectedId);
  const onSelectRef = useRef(onSelect);
  const [internalSelectedId, setInternalSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [webglAvailable, setWebglAvailable] = useState(true);
  const [canvasError, setCanvasError] = useState<string | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  const effectiveSelectedId = selectedId !== undefined ? selectedId : internalSelectedId;
  const nodeMap = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const validEdges = useMemo(
    () => edges.filter((edge) => nodeMap.has(edge.src) && nodeMap.has(edge.dst)),
    [edges, nodeMap],
  );
  const layout = useMemo(() => createLayout(nodes), [nodes]);
  const selectedNode = effectiveSelectedId ? nodeMap.get(effectiveSelectedId) : undefined;
  const formattedSelectedValue = selectedNode ? formatValue(selectedNode) : null;

  selectedIdRef.current = effectiveSelectedId;
  onSelectRef.current = onSelect;

  const requestRender = useCallback(() => {
    const renderer = rendererRef.current;
    const scene = sceneRef.current;
    const camera = cameraRef.current;
    if (!renderer || !scene || !camera || typeof window === "undefined") {
      return;
    }
    if (rafRef.current !== null) {
      return;
    }
    rafRef.current = window.requestAnimationFrame(() => {
      rafRef.current = null;
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    });
  }, []);

  const applyCamera = useCallback(() => {
    const host = canvasHostRef.current;
    const camera = cameraRef.current;
    if (!host || !camera) {
      return;
    }
    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    const aspect = width / height;
    const viewHeight = 10;
    camera.left = (-viewHeight * aspect) / 2;
    camera.right = (viewHeight * aspect) / 2;
    camera.top = viewHeight / 2;
    camera.bottom = -viewHeight / 2;
    camera.position.set(viewRef.current.panX, viewRef.current.panY, 20);
    camera.zoom = viewRef.current.zoom;
    camera.updateProjectionMatrix();
  }, []);

  const fitGraph = useCallback(() => {
    const host = canvasHostRef.current;
    const camera = cameraRef.current;
    const currentLayout = layoutRef.current;
    if (!host || !camera || !currentLayout) {
      return;
    }

    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    const aspect = width / height;
    const availableWidth = Math.max(1, aspect * 10 * 0.86);
    const availableHeight = Math.max(1, 10 * 0.82);
    const graphWidth = Math.max(1, currentLayout.maxX - currentLayout.minX + 1.6);
    const graphHeight = Math.max(1, currentLayout.maxY - currentLayout.minY + 1.8);
    viewRef.current.zoom = Math.min(
      1.55,
      Math.max(0.42, Math.min(availableWidth / graphWidth, availableHeight / graphHeight)),
    );
    viewRef.current.panX = (currentLayout.minX + currentLayout.maxX) / 2;
    viewRef.current.panY = (currentLayout.minY + currentLayout.maxY) / 2;
    applyCamera();
    requestRender();
  }, [applyCamera, requestRender]);

  useEffect(() => {
    const host = canvasHostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas) {
      return undefined;
    }

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, MAX_DPR));
      renderer.setClearColor(0x000000, 0);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    } catch {
      setWebglAvailable(false);
      setCanvasError("WebGL is unavailable; the semantic graph remains available below.");
      return undefined;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-5, 5, 5, -5, 0.1, 100);
    camera.position.set(0, 0, 20);
    rendererRef.current = renderer;
    sceneRef.current = scene;
    cameraRef.current = camera;
    setWebglAvailable(true);
    setCanvasError(null);

    const resize = () => {
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(1, host.clientHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, MAX_DPR));
      renderer.setSize(width, height, false);
      applyCamera();
      requestRender();
    };

    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    resizeObserver?.observe(host);
    if (!resizeObserver) {
      window.addEventListener("resize", resize);
    }
    resize();

    const getCanvasPoint = (event: PointerEvent): THREE.Vector2 => {
      const rect = canvas.getBoundingClientRect();
      return new THREE.Vector2(
        ((event.clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1,
        -((event.clientY - rect.top) / Math.max(1, rect.height)) * 2 + 1,
      );
    };

    const pickNode = (event: PointerEvent): string | null => {
      const currentCamera = cameraRef.current;
      const currentVisuals = visualsRef.current;
      if (!currentCamera || !currentVisuals) {
        return null;
      }
      raycasterRef.current.setFromCamera(getCanvasPoint(event), currentCamera);
      const bodies = [...currentVisuals.nodeVisuals.values()].map((visual) => visual.body);
      const intersection = raycasterRef.current.intersectObjects(bodies, false)[0];
      return typeof intersection?.object.userData.nodeId === "string"
        ? intersection.object.userData.nodeId
        : null;
    };

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) {
        return;
      }
      pointerRef.current = {
        id: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        lastX: event.clientX,
        lastY: event.clientY,
        moved: false,
      };
      canvas.setPointerCapture?.(event.pointerId);
    };

    const onPointerMove = (event: PointerEvent) => {
      const pointer = pointerRef.current;
      if (pointer && pointer.id === event.pointerId) {
        const deltaX = event.clientX - pointer.lastX;
        const deltaY = event.clientY - pointer.lastY;
        if (Math.abs(event.clientX - pointer.x) + Math.abs(event.clientY - pointer.y) > 5) {
          pointer.moved = true;
        }
        if (pointer.moved) {
          const width = Math.max(1, host.clientWidth);
          const height = Math.max(1, host.clientHeight);
          const worldHeight = 10 / Math.max(0.01, viewRef.current.zoom);
          viewRef.current.panX -= (deltaX / width) * worldHeight * (width / height);
          viewRef.current.panY += (deltaY / height) * worldHeight;
          applyCamera();
          requestRender();
        }
        pointer.lastX = event.clientX;
        pointer.lastY = event.clientY;
        return;
      }

      const nextHoveredId = pickNode(event);
      setHoveredId((current) => (current === nextHoveredId ? current : nextHoveredId));
    };

    const onPointerUp = (event: PointerEvent) => {
      const pointer = pointerRef.current;
      if (!pointer || pointer.id !== event.pointerId) {
        return;
      }
      pointerRef.current = null;
      canvas.releasePointerCapture?.(event.pointerId);
      if (!pointer.moved) {
        const nodeId = pickNode(event);
        if (nodeId) {
          if (selectedIdRef.current === undefined) {
            setInternalSelectedId(nodeId);
          }
          onSelectRef.current?.(nodeId);
        }
      }
    };

    const onPointerLeave = () => {
      if (!pointerRef.current) {
        setHoveredId(null);
      }
    };

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const factor = event.deltaY > 0 ? 0.9 : 1.1;
      viewRef.current.zoom = Math.min(2.4, Math.max(0.42, viewRef.current.zoom * factor));
      applyCamera();
      requestRender();
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("pointerleave", onPointerLeave);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      resizeObserver?.disconnect();
      if (!resizeObserver) {
        window.removeEventListener("resize", resize);
      }
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      canvas.removeEventListener("wheel", onWheel);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      if (visualsRef.current) {
        disposeObject(visualsRef.current.root);
        visualsRef.current = null;
      }
      renderer.setAnimationLoop(null);
      renderer.dispose();
      renderer.forceContextLoss?.();
      rendererRef.current = null;
      sceneRef.current = null;
      cameraRef.current = null;
    };
  }, [applyCamera, requestRender]);

  useEffect(() => {
    layoutRef.current = layout;
    const scene = sceneRef.current;
    if (!scene || !webglAvailable) {
      return undefined;
    }

    if (visualsRef.current) {
      scene.remove(visualsRef.current.root);
      disposeObject(visualsRef.current.root);
      visualsRef.current = null;
    }

    const root = new THREE.Group();
    root.name = "assembly-schematic";
    root.add(makeGrid(layout));

    const nodeVisuals = new Map<string, NodeVisual>();
    nodes.forEach((node) => {
      const position = layout.positions.get(node.id);
      if (!position || nodeVisuals.has(node.id)) {
        return;
      }
      const visual = makeNodeVisual(node, position);
      visual.body.userData.nodeId = node.id;
      visual.group.userData.nodeId = node.id;
      nodeVisuals.set(node.id, visual);
      root.add(visual.group);
    });

    const edgeVisuals: Array<{ edge: AssemblyEdge; visual: EdgeVisual }> = [];
    validEdges.forEach((edge) => {
      const source = layout.positions.get(edge.src);
      const destination = layout.positions.get(edge.dst);
      if (!source || !destination) {
        return;
      }
      const visual = makeEdgeVisual(edge, source, destination);
      edgeVisuals.push({ edge, visual });
      root.add(visual.line, visual.arrow);
    });

    scene.add(root);
    visualsRef.current = { root, nodeVisuals, edgeVisuals };
    applyCamera();
    fitGraph();
    requestRender();

    return undefined;
  }, [applyCamera, fitGraph, layout, nodes, requestRender, validEdges, webglAvailable]);

  useEffect(() => {
    const visuals = visualsRef.current;
    if (!visuals) {
      return;
    }
    const selected = selectedIdRef.current;
    const hovered = hoveredId;

    visuals.nodeVisuals.forEach((visual, nodeId) => {
      const isSelected = nodeId === selected;
      const isHovered = nodeId === hovered;
      visual.body.material.color.setHex(
        isSelected ? SCHEMATIC_ORANGE : colorWithAlpha(visual.baseColor, isHovered ? 0.42 : 0.26),
      );
      visual.body.material.opacity = isSelected || isHovered ? 1 : 0.95;
      visual.outline.material.color.setHex(isSelected ? SCHEMATIC_ORANGE : visual.baseColor);
      visual.outline.material.opacity = isSelected ? 1 : isHovered ? 0.98 : 0.9;
      visual.accent.material.color.setHex(isSelected ? SCHEMATIC_ORANGE : visual.baseColor);
      visual.group.scale.setScalar(isSelected ? 1.06 : isHovered ? 1.03 : 1);
    });

    visuals.edgeVisuals.forEach(({ edge, visual }) => {
      const connected = edge.src === selected || edge.dst === selected || edge.src === hovered || edge.dst === hovered;
      const active = edge.src === selected || edge.dst === selected;
      visual.line.material.color.setHex(active ? SCHEMATIC_ORANGE : connected ? SCHEMATIC_CYAN : visual.baseColor);
      visual.line.material.opacity = active ? 0.95 : connected ? 0.82 : 0.65;
      visual.arrow.material.color.setHex(active ? SCHEMATIC_ORANGE : connected ? SCHEMATIC_CYAN : visual.baseColor);
      visual.arrow.material.opacity = active ? 1 : connected ? 0.92 : 0.82;
    });
    requestRender();
  }, [hoveredId, requestRender]);

  const handleSelect = (id: string) => {
    if (selectedId === undefined) {
      setInternalSelectedId(id);
    }
    onSelect?.(id);
  };

  const handleRecenter = () => {
    fitGraph();
  };

  const handleListHover = (id: string | null) => {
    setHoveredId(id);
  };

  const incoming = useMemo(() => {
    const map = new Map<string, AssemblyEdge[]>();
    validEdges.forEach((edge) => {
      const list = map.get(edge.dst) ?? [];
      list.push(edge);
      map.set(edge.dst, list);
    });
    return map;
  }, [validEdges]);

  const outgoing = useMemo(() => {
    const map = new Map<string, AssemblyEdge[]>();
    validEdges.forEach((edge) => {
      const list = map.get(edge.src) ?? [];
      list.push(edge);
      map.set(edge.src, list);
    });
    return map;
  }, [validEdges]);

  return (
    <section
      className="fw-assembly-space"
      data-reduced-motion={reducedMotion ? "true" : "false"}
      aria-labelledby="fw-assembly-space-title"
    >
      <header className="fw-assembly-space__header">
        <div>
          <div className="fw-assembly-space__eyebrow">INDUSTRIAL WORLD / REQUIREMENT FLOW</div>
          <h2 id="fw-assembly-space-title">{title}</h2>
          <p className="fw-assembly-space__subhead">
            Trace the supplied assembly and dependency relationships. Spatial placement follows depth only.
          </p>
        </div>
        <div className="fw-assembly-space__meta" aria-label="Schematic status">
          <span className="fw-assembly-space__badge fw-assembly-space__badge--accent">SCHEMATIC</span>
          <span className="fw-assembly-space__badge">NON-DIMENSIONAL</span>
          <span className="fw-assembly-space__count">
            {nodes.length} node{nodes.length === 1 ? "" : "s"} · {validEdges.length} link{validEdges.length === 1 ? "" : "s"}
          </span>
        </div>
      </header>

      <div className="fw-assembly-space__workspace">
        <div className="fw-assembly-space__canvas-panel">
          <div className="fw-assembly-space__canvas-toolbar">
            <span className="fw-assembly-space__toolbar-note">
              {webglAvailable ? "Depth-led topology · drag to pan · wheel to zoom" : "Canvas unavailable"}
            </span>
            <button className="fw-assembly-space__button" type="button" onClick={handleRecenter}>
              Recenter
            </button>
          </div>
          <div
            ref={canvasHostRef}
            className="fw-assembly-space__canvas-host"
            data-canvas-state={webglAvailable ? "ready" : "unavailable"}
          >
            <canvas
              ref={canvasRef}
              className="fw-assembly-space__canvas"
              aria-label="Non-dimensional industrial assembly schematic"
              tabIndex={0}
            />
            {!webglAvailable && (
              <div className="fw-assembly-space__canvas-message" role="status">
                {canvasError ?? "WebGL is unavailable; use the semantic graph list."}
              </div>
            )}
            {webglAvailable && nodes.length === 0 && (
              <div className="fw-assembly-space__canvas-message">No supplied nodes to plot.</div>
            )}
            {webglAvailable && (
              <div className="fw-assembly-space__canvas-legend" aria-hidden="true">
                <span><i className="fw-assembly-space__legend-dot fw-assembly-space__legend-dot--node" /> supplied node</span>
                <span><i className="fw-assembly-space__legend-dot fw-assembly-space__legend-dot--link" /> supplied link</span>
              </div>
            )}
          </div>
          <div className="fw-assembly-space__canvas-caption">
            Geometry is a visual index, not a drawing, capacity model, or physical scale.
          </div>
        </div>

        <aside className="fw-assembly-space__semantic" aria-label="Semantic assembly graph">
          <div className="fw-assembly-space__semantic-head">
            <div>
              <div className="fw-assembly-space__section-label">SEMANTIC 2D VIEW</div>
              <p>Keyboard-selectable records from the supplied graph.</p>
            </div>
            {selectedNode && <span className="fw-assembly-space__selected-mark">SELECTED</span>}
          </div>

          <div className="fw-assembly-space__selection-status" aria-live="polite">
            {selectedNode ? (
              <>
                <strong>{selectedNode.label}</strong>
                <span>
                  {selectedNode.kind} · depth {String(selectedNode.depth)}
                  {formattedSelectedValue ? ` · ${formattedSelectedValue}` : ""}
                </span>
              </>
            ) : (
              <span>Select a node to inspect its supplied record.</span>
            )}
          </div>

          {nodes.length > 0 ? (
            <ol className="fw-assembly-space__node-list">
              {nodes.map((node) => {
                const value = formatValue(node);
                const isSelected = effectiveSelectedId === node.id;
                const isHovered = hoveredId === node.id;
                const nodeIncoming = incoming.get(node.id) ?? [];
                const nodeOutgoing = outgoing.get(node.id) ?? [];
                return (
                  <li key={`${node.id}-${node.label}`}>
                    <button
                      type="button"
                      className="fw-assembly-space__node-button"
                      data-selected={isSelected ? "true" : "false"}
                      data-hovered={isHovered ? "true" : "false"}
                      onClick={() => handleSelect(node.id)}
                      onMouseEnter={() => handleListHover(node.id)}
                      onMouseLeave={() => handleListHover(null)}
                      onFocus={() => handleListHover(node.id)}
                      onBlur={() => handleListHover(null)}
                      aria-pressed={isSelected}
                      aria-label={`${node.label}, ${node.kind}, depth ${String(node.depth)}`}
                    >
                      <span className="fw-assembly-space__node-swatch" style={{ backgroundColor: `#${colorForKind(node.kind).toString(16).padStart(6, "0")}` }} />
                      <span className="fw-assembly-space__node-copy">
                        <span className="fw-assembly-space__node-name">{node.label || node.id}</span>
                        <span className="fw-assembly-space__node-kind">
                          {node.kind || "—"} · depth {String(node.depth)}
                        </span>
                        {(value || node.epistemicClass) && (
                          <span className="fw-assembly-space__node-facts">
                            {value && <span>{value}</span>}
                            {node.epistemicClass && <span className="fw-assembly-space__epistemic">{node.epistemicClass}</span>}
                          </span>
                        )}
                        {(nodeIncoming.length > 0 || nodeOutgoing.length > 0) && (
                          <span className="fw-assembly-space__node-links">
                            {nodeIncoming.length > 0 && <span>in {nodeIncoming.length}</span>}
                            {nodeOutgoing.length > 0 && <span>out {nodeOutgoing.length}</span>}
                          </span>
                        )}
                      </span>
                      <span className="fw-assembly-space__node-chevron" aria-hidden="true">↗</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="fw-assembly-space__empty-state">
              No nodes were supplied. The semantic view will populate when the assembly graph is available.
            </div>
          )}

          {validEdges.length > 0 && (
            <details className="fw-assembly-space__links-details">
              <summary>Supplied links ({validEdges.length})</summary>
              <ul>
                {validEdges.map((edge, index) => (
                  <li key={`${edge.src}-${edge.dst}-${edge.relation}-${index}`}>
                    <span>{nodeMap.get(edge.src)?.label ?? edge.src}</span>
                    <span className="fw-assembly-space__relation">{edge.relation || "link"}</span>
                    <span>{nodeMap.get(edge.dst)?.label ?? edge.dst}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </aside>
      </div>
    </section>
  );
}
