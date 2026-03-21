import { Button } from "@/components/ui/button"
import { useStore, type Node } from "@xyflow/react"
import { useCallback } from "react"

// Transform selector to get zoom & pan values
const transformSelector = (state: any) => state.transform

interface SidebarProps {
  nodes: Node[]
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

export default function Sidebar({ nodes, setNodes }: SidebarProps) {
  const transform = useStore(transformSelector)

  const selectAll = useCallback(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        selected: true,
      }))
    )
  }, [setNodes])

  return (
    <aside className="flex flex-col border-l border-gray-200 bg-white p-4 text-xs md:h-auto md:w-1/5 md:max-w-[250px]">
      <div className="mb-2 text-gray-600">
        This is an example of how you can access the internal state outside of
        the ReactFlow component.
      </div>

      <div className="mb-1 font-bold">Zoom & pan transform</div>
      <div className="mb-5">
        [{transform[0].toFixed(2)}, {transform[1].toFixed(2)},{" "}
        {transform[2].toFixed(2)}]
      </div>

      <div className="mb-1 font-bold">Nodes</div>
      <div className="mb-2 space-y-1">
        {nodes.map((node) => (
          <div key={node.id} className="text-gray-700">
            Node {node.id} - x: {node.position.x.toFixed(2)}, y:{" "}
            {node.position.y.toFixed(2)}
          </div>
        ))}
      </div>

      <div className="mt-2">
        <Button onClick={selectAll} size="sm" className="w-full">
          Select All Nodes
        </Button>
      </div>
    </aside>
  )
}
