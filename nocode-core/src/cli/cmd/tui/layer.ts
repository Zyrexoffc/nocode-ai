import { Layer } from "effect"
import { TuiConfig } from "./config/tui"
import { Npm } from "@nocode-ai-ai/core/npm"
import { Observability } from "@nocode-ai-ai/core/effect/observability"

export const CliLayer = Observability.layer.pipe(Layer.merge(TuiConfig.layer), Layer.provide(Npm.defaultLayer))
