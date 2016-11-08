loadScript("/commons/scripts/Utils.js");
loadStyle("/commons/styles/ZebraTable.css");

function paintZebraTable(table)
{
  var i = 0;
  for (var j = 0, row; row = table.rows[j]; ++j)
  {
    if (!isVisible(row) || isaClass("Linked", row)) continue;
    if(i++ % 2)
    {
      switchClass("EvenRow", "OddRow", row);
    }
    else
    {
      switchClass("OddRow", "EvenRow", row);
    }
  }
}

function initZebra()
{
  var tables = document.getElementsByTagName("table");
  for (var i = 0, table; table = tables[i]; ++i)
  {
    if (isaClass("Zebra", table)) paintZebraTable(table);
  }
}

addLoadEvent(initZebra);
