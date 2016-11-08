loadScript("/commons/scripts/Utils.js");
loadStyle("/commons/styles/ExpandableTable.css");

function initExpandable()
{
  var tables = document.getElementsByTagName("table");
  for (var tbl_idx = 0; tbl_idx < tables.length; ++tbl_idx)
  {
    var table = tables[tbl_idx];
    if (!isaClass("Expandable", table)) continue;
    var expanded = false;
    var rows = table.rows;
    for (var i = 0; i < rows.length; ++i)
    {
      var current_row = rows[i];
      var new_td = current_row.insertCell(0);
      if (current_row.parentNode.nodeName == "THEAD") continue;
      if (isaClass("Linked", current_row))
      {
        if (expanded) current_row.style.display = "table-row";
        else current_row.style.display = "none";
        continue;
      }
      var next_row = rows.item(i + 1);
      if (! next_row) continue;
      if (isaClass("Linked", next_row))
      {
        if (isaClass("Expanded", current_row))
        {
          expanded = true;
        }
        else
        {
          addClass("Collapsed", current_row);
          expanded = false;
        }
        addClass("ExpandIcon", new_td);
        new_td.onclick = expand;
      }
    }
  }
};

function expand(e)
{
  var clicked_element = window.event
    ? window.event.srcElement
    : e.currentTarget;

  while (clicked_element.tagName.toLowerCase() != "tr")
  {
    clicked_element = clicked_element.parentNode;
  }
  var display;
  if (isaClass("Collapsed", clicked_element))
  {
    switchClass("Collapsed", "Expanded", clicked_element);
    display = "table-row";
  }
  else
  {
    switchClass("Expanded", "Collapsed", clicked_element);
    display = "none";
  }
  for (var row = get_next_element(clicked_element);
       row && isaClass("Linked", row);
       row = get_next_element(row))
  {
    row.style.display = display;
  }
};

addLoadEvent(initExpandable);
