import jsYaml from "js-yaml"

export default {
  dump(obj: unknown): string {
    return jsYaml.dump(obj, { indent: 2, lineWidth: 120 })
  },
}
