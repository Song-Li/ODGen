function upload_file() {
  $("#readyimg").remove();
  $("#errormsg").remove();
  $('#entrance-file').remove();
  var form_data = new FormData($('#uploadfile')[0]);
  $.ajax({
    url: '/upload',
    type: 'POST',
    data: form_data,
    contentType: false,
    cache: false,
    processData: false,
    success: function(data){
      if (data != "success"){
        $("#uploaditems").append('<img id="readyimg" class="img" src="/imgs/error.gif"/>');
        $("#uploaditems").append('<div id="errormsg" class="show-error">' + data + '</div>');
      } else {
        $("#uploaditems").append('<img id="readyimg" class="img" src="/imgs/ok.gif"/>');
        load_file_tree();
      }
    }
  });
}

function check_progress() {
  var id = setInterval(frame, 100);
  function frame() {
    $.ajax({
      url: '/progress',
      type: 'GET',
      success: function(data){
        if (data >= 100) clearInterval(id)
        if ($('#progress').val() >= 100) return ;
        $('#progress').val(20 * data);
      }
    });
  }
  return id;
}

function updateTaintedHighlightInEditor(){
  let curFile = $("#editor-title").text().split(' ')[1];
  editor.session.setMode("ace/mode/javascript");
  let session = editor.getSession();
  let curMarks = session.getMarkers(true)
  for(let curTaint in curMarks) session.removeMarker(curTaint)
  $.ajax({
    url: '/getTainteds',
    type: 'GET',
    dataType: "json",
    success: (response) => {
      if(!response || !response[curFile]) return null; 
      for(let rangeText of response[curFile]){
        let ntj = JSON.parse(rangeText)
        let newRange = new ace.Range(
          ntj.start.row-1, ntj.start.column, 
          ntj.end.row-1, ntj.end.column
        )
        session.addMarker(newRange, 'text-ace', 'text', true)
      }
    }
  });
}

function show_in_editor(filename, data, lineno) {
  $("#editor-title").html("Editor: " + filename);
  var editor = ace.edit('editor');
  var Range = ace.require('ace/range').Range;

  if (editor.marker != undefined) {
    editor.session.removeMarker(editor.marker);
  }
  if(lineno > 0) {
    editor.marker = editor.session.addMarker(
      new Range(lineno - 1, 0, lineno - 1, 1), "myMarker", "fullLine"
    );
  }
  editor.setValue(data);
  editor.clearSelection();
  editor.moveCursorTo(lineno, 0);
  editor.gotoLine(lineno, 0, true);
  updateTaintedHighlightInEditor()
}

function send_click(data, lineno){
  $.ajax({
    url: '/getFile',
    type: 'POST',
    data: JSON.stringify({'name': data}),
    contentType: "application/json",
    dataType: 'html',
    success: function(succ){
      show_in_editor(data, succ, lineno);
    }
  });
}

function start_check() {
  $('#progress').val(0);
  progress_id = check_progress(0, 0);
  $.ajax({
    url: '/check',
    type: 'POST',
    data: $('#options').serialize(),
    success: function(data){
      clearInterval(progress_id);
      if (data == "Not detected") {
        $("#cy").html(data);
      } else {
        eval(data);
      }
      $('#progress').val(100);
    }
  });
}

selected_entrance = "";

function load_file_tree() {
  console.log("try to list file");
  $('#filetree').remove();
  $('#filetree-container').append('<div id="filetree"></div>');
  $('#filetree').fileTree({
    script: 'listdir'
  }, function(file) {
    // do something with file
    $('.selected-file').text( $('a[rel="'+file+'"]').text() );
    send_click(file, 0);
  }).on('filetreeclicked', function(e, data)	{ selected_entrance = data.rel; console.log(data.value, data.rel); });
}

function set_entrance_file() {
  $.ajax({
    url: '/setEntrance',
    type: 'POST',
    data: JSON.stringify({'file': selected_entrance}),
    contentType: "application/json",
    dataType: 'html',
    success: function(succ){
      $('#entrance-file').remove();
      $("#start-container").append('<div id="entrance-file"> Entrance file set as: ' + selected_entrance + '</div>');
    }
  });
}


function setup_editor(){
  editor = ace.edit("editor");
  editor.session.setMode("ace/mode/javascript");
  var session = editor.getSession();
  var start_pos = -1, end_pos = -1;
  session.selection.on("changeSelection", function() {
    var range = session.selection.getRange(); 
    start_pos = range.start;
    end_pos = range.end;
    console.log(start_pos, end_pos);
  });

  const contextMenu = document.getElementById("context-menu");
  const scope = document.querySelector("body");

  const normalizePozition = (mouseX, mouseY) => {
    // ? compute what is the mouse position relative to the container element (scope)
    let {
      left: scopeOffsetX,
      top: scopeOffsetY,
    } = scope.getBoundingClientRect();

    scopeOffsetX = scopeOffsetX < 0 ? 0 : scopeOffsetX;
    scopeOffsetY = scopeOffsetY < 0 ? 0 : scopeOffsetY;

    const scopeX = mouseX - scopeOffsetX;
    const scopeY = mouseY - scopeOffsetY;

    clientHeight = Math.max( window.innerHeight, scope.clientHeight);
    clientWidth = Math.max( window.innerWidth, scope.clientWidth);

    const outOfBoundsOnX =
      scopeX + contextMenu.clientWidth > clientWidth;

    const outOfBoundsOnY =
      scopeY + contextMenu.clientHeight > clientHeight;

    let normalizedX = mouseX;
    let normalizedY = mouseY;

    if (outOfBoundsOnX) {
      normalizedX =
        scopeOffsetX + clientWidth - contextMenu.clientWidth;
    }

    // ? normalize on Y
    if (outOfBoundsOnY) {
      normalizedY =
        scopeOffsetY + clientHeight - contextMenu.clientHeight;
    }

    return { normalizedX, normalizedY };
  };

  editor.container.addEventListener("contextmenu", (event) => {
    event.preventDefault();

    const { clientX: mouseX, clientY: mouseY } = event;

    const { normalizedX, normalizedY } = normalizePozition(mouseX, mouseY);

    contextMenu.classList.remove("visible");

    contextMenu.style.top = `${normalizedY}px`;
    contextMenu.style.left = `${normalizedX}px`;

    setTimeout(() => {
      contextMenu.classList.add("visible");
    });
  });
  scope.addEventListener("click", (e) => {
    if (e.target.offsetParent != contextMenu) {
      contextMenu.classList.remove("visible");
    }
  });
}

function get_editor_selection() {
  editor = ace.edit("editor");
  editor.session.setMode("ace/mode/javascript");
  var session = editor.getSession();
  return editor.getSelectedText()
  /*
  session.selection.on("changeSelection", function() {
    var range = session.selection.getRange(); 
    start_pos = range.start;
    end_pos = range.end;
    console.log(start_pos, end_pos);
  });
  */
}

function get_editor_selection_range() {
  editor = ace.edit("editor");
  editor.session.setMode("ace/mode/javascript");
  var session = editor.getSession();
  var range = session.selection.getRange();
  // by default, the row number starts from 0
  // we need to +1
  range['start']['row'] ++;
  range['end']['row'] ++;
  return range

}

function set_as_entrance() {
  /**
   * this function is specifically for setting a function as entrance
   */
  const contextMenu = document.getElementById("context-menu");
  contextMenu.classList.remove("visible");
  var selected_text = get_editor_selection();
  console.log(selected_text);
  $.ajax({
    url: '/setEntranceFunc',
    type: 'POST',
    data: JSON.stringify({'func': selected_text}),
    contentType: "application/json",
    dataType: 'html',
    success: function(succ){
      $('#entrance-file').remove();
      $("#start-container").append('<div id="entrance-file"> Entrance function set as: ' + selected_text + '</div>');
    }
  });
}

function mark_tainted() {
  /**
   * this function is specifically for setting a var as tainted 
   */
  // clear the menu
  const contextMenu = document.getElementById("context-menu");
  contextMenu.classList.remove("visible");

  var selected_range= get_editor_selection_range();
  selected_range['text'] = get_editor_selection();
  console.log(selected_range);
  $.ajax({
    url: '/markTainted',
    type: 'POST',
    data: JSON.stringify({'var': selected_range}),
    contentType: "application/json",
    dataType: 'html',
    success: function(succ){
      updateTaintedHighlightInEditor()
      $('#entrance-file').remove();
      $("#start-container").append('<div id="entrance-file"> ' + selected_range['text'] + ' is mark as tainted</div>');
    }
  });
}
