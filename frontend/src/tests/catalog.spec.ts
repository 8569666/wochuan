import { expect, it } from 'vitest'
import { buildMatrix } from '../components/matrix'

const colors = [1,2,3].map(id => ({id,code:`C${id}`,name:`颜色${id}`}))
const sizes = [1,2,3,4].map(id => ({id,code:`S${id}`,name:`尺码${id}`}))
it('generates twelve distinct color and size cells', () => {
  const result = buildMatrix(colors, sizes, [], '599.00')
  expect(result).toHaveLength(12)
  expect(new Set(result.map(c => `${c.color_id}:${c.size_id}`)).size).toBe(12)
})
it('preserves entered values and removes deselected cells', () => {
  const previous = buildMatrix(colors, sizes, [], '599.00')
  previous[0]!.retail_price = '199.00'
  const result = buildMatrix(colors.slice(0,1), sizes, previous, '599.00')
  expect(result).toHaveLength(4)
  expect(result[0]!.retail_price).toBe('199.00')
})
