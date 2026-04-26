import { describe, expect, test } from "bun:test"
import path from "path"
import { Global } from "@nocode-ai-ai/core/global"
import { InstallationChannel } from "@nocode-ai-ai/core/installation/version"
import { Database } from "../../src/storage"

describe("Database.Path", () => {
  test("returns database path for the current channel", () => {
    const expected = ["latest", "beta"].includes(InstallationChannel)
      ? path.join(Global.Path.data, "nocode-ai.db")
      : path.join(Global.Path.data, `nocode-ai-${InstallationChannel.replace(/[^a-zA-Z0-9._-]/g, "-")}.db`)
    expect(Database.getChannelPath()).toBe(expected)
  })
})
