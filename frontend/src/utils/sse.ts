const SSE_TIMEOUT_MS = 60000

export async function readSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: string, data: any) => void,
  signal?: AbortSignal,
): Promise<void> {
  const decoder = new TextDecoder()
  let buffer = ''
  let lastReadTime = Date.now()

  while (true) {
    if (Date.now() - lastReadTime > SSE_TIMEOUT_MS) {
      throw new Error('SSE 连接超时: 60 秒未收到数据')
    }

    let done: boolean
    let value: Uint8Array | undefined

    try {
      const readResult = await reader.read()
      done = readResult.done
      value = readResult.value
    } catch (err: any) {
      if (signal?.aborted) break
      throw err
    }

    if (done) break
    if (signal?.aborted) break

    lastReadTime = Date.now()
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let currentEvent = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) currentEvent = line.slice(7).trim()
      else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6).trim())
          onEvent(currentEvent, data)
        } catch {}
      }
    }
  }
}
