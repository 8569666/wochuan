import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('../', import.meta.url))
const design = readFileSync(root+'DESIGN.md','utf8')
const css = readFileSync(root+'frontend/src/styles.css','utf8')
for (const name of ['primary','background','surface','sidebar','text','muted','border','danger']) {
  const expected = design.match(new RegExp(`  ${name}: "(#[0-9a-fA-F]+)"`))?.[1]
  const actual = css.match(new RegExp(`--${name}:(#[0-9a-fA-F]+)`))?.[1]
  if(!expected || expected !== actual) throw new Error(`Design token drift: ${name}`)
}
console.log('Design tokens match all eight documented colors.')
