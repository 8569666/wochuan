import type { MatrixCell } from '../api/types'

export function buildMatrix(colors: {id:number}[], sizes: {id:number}[], previous: MatrixCell[], defaultPrice: string): MatrixCell[] {
  const map = new Map(previous.map(cell => [`${cell.color_id}:${cell.size_id}`, cell]))
  return colors.flatMap(color => sizes.map(size => ({...(map.get(`${color.id}:${size.id}`) || {color_id:color.id,size_id:size.id,retail_price:defaultPrice})})))
}
