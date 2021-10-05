var cy = window.cy = cytoscape({
  container: document.getElementById('cy'),

  boxSelectionEnabled: false,

  style: [
    {
      selector: 'node',
      css: {
        'content': 'data(content)',
        'text-wrap': 'wrap',
        'shape': 'rectangle', 
        'width': "data(width)",
        'font-size': 8,
        'text-valign': 'center',
        'text-halign': 'left'
      }
    },
    {
      selector: ':parent',
      css: {
        'text-valign': 'top',
        'shape': 'rectangle',
        'text-halign': 'center',
      }
    },
    {
      selector: 'edge',
      css: {
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle'
      }
    }
  ],

  elements: {
    nodes: [
      { data: { "id": 'a', parent: 'b', "content": "aasdfsssssssssssssssss\nb" }, position: { x: 100, y: 0 } },
      { data: { id: 'b' } },
      { data: { id: 'c', parent: 'b' }, position: { x: 100, y: 200} },
      { data: { id: 'd' }, position: { x: 215, y: 175 } },
      { data: { id: 'e' } },
      { data: { id: 'function root()', parent: 'e' , width: 350}, position: { x: 300, y: 175 } }
    ],
    edges: [
      { data: { id: 'ad', source: 'a', target: 'd' } },
      { data: { id: 'eb', source: 'e', target: 'b' } }

    ]
  },

  layout: {
    name: 'preset',
    padding: 5
  }
});


