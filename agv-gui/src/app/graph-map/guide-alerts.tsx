import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangleIcon, CheckCircle2Icon } from "lucide-react"

export function GuideAlerts() {
  return (
    <div className="grid w-full grid-cols-2 items-start gap-4">
      <Alert>
        <CheckCircle2Icon />
        <AlertTitle>Add new node</AlertTitle>
        <AlertDescription>
          Drag from the right handle of a node N to a blank space, then release
          mouse to create a new node N+1. An edge will be formed between these
          two nodes, where node N is the source and node N+1 is the target.
        </AlertDescription>
      </Alert>
      <Alert>
        <CheckCircle2Icon />
        <AlertTitle>Create edge between existing nodes</AlertTitle>
        <AlertDescription>
          To create an edge between two existing nodes, drag from the right
          handle of a node N to the left handle of another node M, then release
          mouse. An edge will be formed between these two nodes, where node N is
          the source and node M is the target.
        </AlertDescription>
      </Alert>
      <Alert className="border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-50">
        <AlertTriangleIcon />
        <AlertTitle>Delete a node</AlertTitle>
        <AlertDescription>
          Click a node to select it, then press <kbd>Backspace</kbd> to delete
          it. Note that deleting a node will also delete all edges connected to
          it.
        </AlertDescription>
      </Alert>
    </div>
  )
}
