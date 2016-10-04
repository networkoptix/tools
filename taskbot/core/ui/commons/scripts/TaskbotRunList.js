function highlight_anchor(event)
{
  var historyList = document.getElementById("historyList");
  if (event.type == "hashchange")
  {
    var old_hash = event.oldURL.substring(event.oldURL.search('#') + 1);
    var old_element = document.getElementById(old_hash);
    if (old_element)
    {
      var cell = old_element;
      do
      {
        removeClass("Transparent", historyList);
        removeClass("SelectedTask", cell);
      } while ((cell = get_next_element(cell)) && !(cell.id && cell.id.match("task[0-9]+")))
    }

    new_hash = event.newURL.substring(event.newURL.search('#') + 1);
  }
  else // event type is load
  {
    new_hash = window.location.hash.substring(1);
  }

  var new_element = document.getElementById(new_hash);
  if (new_element)
  {
    var cell = new_element;
    do
    {
      addClass("Transparent", historyList);
      addClass("SelectedTask", cell);
    } while ((cell = get_next_element(cell)) && !(cell.id && cell.id.match("task[0-9]+")))
  }
}

function init(event)
{
  var state = false;
  window.onhashchange = highlight_anchor;
  highlight_anchor(event);
  var historyList = document.getElementById("historyList");
  
  document.onclick = function(e)
  {
    var element = e.srcElement || e.target;
    do
    {
      if (isaClass("SelectedTask", element)) return;
    } while (element = element.parentNode)
    removeClass("Transparent", historyList);
  }
}

addLoadEvent(init);
