import {
  BaseEdge,
  getStraightPath,
  useInternalNode,
  type EdgeProps,
} from "@xyflow/react"

export function FloatingEdge({
  id,
  source,
  target,
  markerEnd,
  style,
}: EdgeProps) {
  const sourceNode = useInternalNode(source)
  const targetNode = useInternalNode(target)

  if (!sourceNode || !targetNode) {
    return null
  }

  // Calculate center of source node
  const sx =
    sourceNode.internals?.positionAbsolute?.x !== undefined
      ? sourceNode.internals.positionAbsolute.x +
        (sourceNode.measured?.width ?? 50) / 2
      : sourceNode.position.x
  const sy =
    sourceNode.internals?.positionAbsolute?.y !== undefined
      ? sourceNode.internals.positionAbsolute.y +
        (sourceNode.measured?.height ?? 50) / 2
      : sourceNode.position.y

  // Calculate center of target node
  const tx =
    targetNode.internals?.positionAbsolute?.x !== undefined
      ? targetNode.internals.positionAbsolute.x +
        (targetNode.measured?.width ?? 50) / 2
      : targetNode.position.x
  const ty =
    targetNode.internals?.positionAbsolute?.y !== undefined
      ? targetNode.internals.positionAbsolute.y +
        (targetNode.measured?.height ?? 50) / 2
      : targetNode.position.y

  const dx = tx - sx
  const dy = ty - sy
  const dist = Math.sqrt(dx * dx + dy * dy)

  if (dist === 0) return null

  // 25px radius + 1px for border + 2px padding
  const radius = 28
  const ux = dx / dist
  const uy = dy / dist

  // only draw if nodes are further apart than 2 * radius
  if (dist <= 2 * radius) return null

  const sourceX = sx + radius * ux
  const sourceY = sy + radius * uy
  const targetX = tx - radius * ux
  const targetY = ty - radius * uy

  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  return (
    <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />
  )
}
