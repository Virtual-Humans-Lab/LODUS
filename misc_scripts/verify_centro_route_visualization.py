"""Small CDP smoke test for the Centro route visualization."""

from __future__ import annotations

import json
import urllib.request
import base64
import time
from pathlib import Path

import websocket


tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9223/json"))
tab = next(
    item
    for item in tabs
    if item.get("url", "").endswith("centro-historico-route-explorer.html")
)
socket = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=10)
socket.send(json.dumps({"id": 0, "method": "Page.reload"}))
time.sleep(2)


def evaluate(identifier: int, expression: str):
    socket.send(
        json.dumps(
            {
                "id": identifier,
                "method": "Runtime.evaluate",
                "params": {"expression": expression, "returnByValue": True},
            }
        )
    )
    while True:
        message = json.loads(socket.recv())
        if message.get("id") == identifier:
            return message["result"]["result"].get("value")


initial = evaluate(
    1,
    """JSON.stringify({
      ready: document.readyState,
      sectors: document.querySelectorAll('.leaflet-overlay-pane path.leaflet-interactive').length,
      markers: document.querySelectorAll('.leaflet-markers-pane path').length,
      tiles: document.querySelectorAll('.leaflet-tile-loaded').length,
      bars: document.querySelectorAll('rect.bar').length,
      stylesheets: Array.from(document.styleSheets).map(sheet => sheet.href || 'inline'),
      mapSize: [document.querySelector('#map').clientWidth, document.querySelector('#map').clientHeight]
    })""",
)
layout = evaluate(
    4,
    """JSON.stringify({
      center: map.getCenter(),
      zoom: map.getZoom(),
      bounds: sectorLayer.getBounds(),
      mapRect: document.querySelector('#map').getBoundingClientRect().toJSON(),
      firstPathRect: document.querySelector('.leaflet-overlay-pane path.leaflet-interactive').getBoundingClientRect().toJSON()
    })""",
)
interaction = evaluate(
    2,
    """(() => {
      const path = document.querySelector('.leaflet-overlay-pane path.leaflet-interactive');
      path.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
      return JSON.stringify({
        routePaths: document.querySelectorAll('.leaflet-routes-pane path').length,
        tooltips: document.querySelectorAll('.leaflet-tooltip').length,
        selection: document.querySelector('#selection').innerText
      });
    })()""",
)
after_exit = evaluate(
    5,
    """(() => {
      const path = document.querySelector('.leaflet-overlay-pane path.leaflet-interactive');
      path.dispatchEvent(new MouseEvent('mouseout', {bubbles: true}));
      return JSON.stringify({
        routePaths: document.querySelectorAll('.leaflet-routes-pane path').length,
        tooltips: document.querySelectorAll('.leaflet-tooltip').length
      });
    })()""",
)
time.sleep(0.35)
after_fade = evaluate(
    6,
    """JSON.stringify({
      routePaths: document.querySelectorAll('.leaflet-routes-pane path').length,
      tooltips: document.querySelectorAll('.leaflet-tooltip').length,
      visibleTooltips: Array.from(document.querySelectorAll('.leaflet-tooltip')).filter(
        node => getComputedStyle(node).opacity !== '0'
      ).length
    })""",
)
tab_state = evaluate(
    7,
    """(() => {
      document.querySelector('#time-tab').click();
      return JSON.stringify({
        distanceSelected: document.querySelector('#distance-tab').getAttribute('aria-selected'),
        timeSelected: document.querySelector('#time-tab').getAttribute('aria-selected'),
        distanceHidden: document.querySelector('#distance-panel').hidden,
        timeHidden: document.querySelector('#time-panel').hidden,
        timeBars: document.querySelectorAll('#time-panel rect.bar').length
      });
    })()""",
)
socket.send(json.dumps({"id": 3, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
while True:
    screenshot_message = json.loads(socket.recv())
    if screenshot_message.get("id") == 3:
        break
Path(
    "docs/results/spatial_validation/centro-historico-route-explorer-preview.png"
).write_bytes(base64.b64decode(screenshot_message["result"]["data"]))
print("Initial:", initial)
print("Layout:", layout)
print("After hover:", interaction.encode("unicode_escape").decode("ascii"))
print("After exit:", after_exit)
print("After fade:", after_fade)
print("Travel-time tab:", tab_state)
socket.close()
