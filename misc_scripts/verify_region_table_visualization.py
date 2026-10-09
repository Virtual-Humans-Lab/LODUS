"""CDP smoke test for the region travel-time visualization."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path

import websocket


tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9223/json"))
tab = next(item for item in tabs if item.get("type") == "page" and item["url"].startswith("http://127.0.0.1"))
socket = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=10)


def command(identifier: int, method: str, params=None):
    socket.send(json.dumps({"id": identifier, "method": method, "params": params or {}}))
    while True:
        message = json.loads(socket.recv())
        if message.get("id") == identifier:
            return message.get("result", {})


def evaluate(identifier: int, expression: str):
    result = command(
        identifier,
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True},
    )
    return result["result"].get("value")


command(
    1,
    "Page.navigate",
    {"url": "http://127.0.0.1:8765/region-travel-time-explorer.html"},
)
time.sleep(2)
initial = evaluate(
    2,
    """JSON.stringify({
      ready: document.readyState,
      regions: document.querySelectorAll('.leaflet-overlay-pane path.leaflet-interactive').length,
      tiles: document.querySelectorAll('.leaflet-tile-loaded').length,
      bars: document.querySelectorAll('rect.bar').length,
      allPairs: allPairs.length,
      selected: selectedOrigin
    })""",
)
selected = evaluate(
    3,
    """(() => {
      const layer = layerByName.get('Centro Histórico');
      layer._path.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
      return JSON.stringify({
        selected: selectedOrigin,
        status: document.querySelector('#status').innerText,
        distanceSubtitle: document.querySelector('#distance-subtitle').innerText,
        bars: document.querySelectorAll('rect.bar').length,
        coloredRegions: Array.from(document.querySelectorAll('.leaflet-overlay-pane path')).filter(
          path => path.getAttribute('fill-opacity') === '0.82'
        ).length
      });
    })()""",
)
screenshot = command(4, "Page.captureScreenshot", {"format": "png"})
Path("docs/results/spatial_validation/region-travel-time-explorer-preview.png").write_bytes(
    base64.b64decode(screenshot["data"])
)
escaped = evaluate(
    5,
    """(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
      return JSON.stringify({selected: selectedOrigin, subtitle: document.querySelector('#distance-subtitle').innerText});
    })()""",
)
outside_click = evaluate(
    6,
    """(() => {
      selectRegion('Sarandi');
      map.fire('click');
      return JSON.stringify({selected: selectedOrigin, subtitle: document.querySelector('#duration-subtitle').innerText});
    })()""",
)
print("Initial:", initial)
print("Selected:", selected.encode("unicode_escape").decode("ascii"))
print("Escape:", escaped)
print("Outside click:", outside_click)
socket.close()
