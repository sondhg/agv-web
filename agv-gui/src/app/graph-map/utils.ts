export const getNodeColor = (type?: string) => {
  switch (type) {
    case "PICKUP":
      return "#3b82f6" // blue-500
    case "DELIVERY":
      return "#22c55e" // green-500
    case "CHARGING":
      return "#eab308" // yellow-500
    case "DEFAULT":
    default:
      return "#808080" // white
  }
}
