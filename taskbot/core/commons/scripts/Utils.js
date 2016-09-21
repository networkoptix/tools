// Checks whether element is a instance of classname
function isaClass(classname, element)
{
  var re = new RegExp("\\b"+classname+"\\b", "g");
  return re.test(element.className);
}

// Switcher: removes 'from' class from element and adds 'to' class
function switchClass(from, to, element)
{
  removeClass(from, element);
  addClass(to, element);
}

// Adds 'classname' class to element
function addClass( classname, element )
{
  if(isaClass(classname, element)) return;
  var cn = element.className;
  if( cn != '' )
  {
    classname = ' ' + classname;
  }
  element.className = cn + classname;
}

// Removes 'classname' class from element
function removeClass( classname, element )
{
  var rxp = new RegExp( "\\s?\\b"+classname+"\\b", "g" );
  element.className = element.className.replace( rxp, '' );
}

// Get node that follows current
function getNextElement(current)
{
  var next_element = current.nextSibling;
  while (next_element && next_element.nodeType != 1)
  {
    next_element = next_element.nextSibling;
  }
  return next_element;
}

// alias
function get_next_element(current)
{
  return getNextElement(current);
}

function getPrevElement(current)
{
  var prev_element = current.previousSibling;
  while (prev_element && prev_element.nodeType != 1)
  {
    prev_element = prev_element.previousSibling;
  }
  return prev_element;
}

function isVisible(element)
{
  return !(element.style.display === "none");
}

function jsonpRequest(url, callbackName)
{
  var head = document.getElementsByTagName('head')[0];
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = url + (url.indexOf('?') != -1 ? "&" : "?") +
    "jsonp=" + callbackName +
    "&callback=" + callbackName +
    "&jsonp-callback=" + callbackName +
    "&fake-no-cache=" + new Date().getTime();
  head.appendChild(script);
}

function wrapElement(element, wrapperTag)
{
  var wrapper = document.createElement(wrapperTag);
  element.parentNode.replaceChild(wrapper, element);
  wrapper.appendChild(element);
  return wrapper;
}

function getCurrentStyle(element)
{
  return element.currentStyle || window.getComputedStyle(element);
}

function getHTTPRequestObject()
{
  var request = false;
  try
  {
    request = new XMLHttpRequest();
  }
  catch (trymicrosoft)
  {
    try
    {
      request = new ActiveXObject("Msxml2.XMLHTTP");
    }
    catch (othermicrosoft)
    {
      try
      {
        request = new ActiveXObject("Microsoft.XMLHTTP");
      }
      catch (failed)
      {
        request = false;
      }
    }
  }
  if (!request) alert("Error initializing XMLHttpRequest!");
  return request;
}

function removeChildNodes(element)
{
  while (element.firstChild)
  {
    element.removeChild(element.firstChild);
  }
}

function mergeObjects(o1, o2)
{
  var result = new Object();
  for (var attr in o1) { result[attr] = o1[attr]; }
  for (var attr in o2) { result[attr] = o2[attr]; }
  return result;
}

function isEmpty(obj)
{
  for(var p in obj)
    return false;
  return true;
};

function getCaretPosition (ctrl)
{
  var caretPos = 0;
  // IE Support
  if (document.selection) {
 
    ctrl.focus();
    var sel = document.selection.createRange ();
 
    sel.moveStart ('character', -ctrl.value.length);
 
    caretPos = sel.text.length;
  }
  // Firefox support
  else if (ctrl.selectionStart || ctrl.selectionStart == '0')
    caretPos = ctrl.selectionStart;
 
  return caretPos;
}

function hasVerticalScroll()
{
  // The Modern solution
  if (typeof window.innerWidth === 'number')
    return window.innerWidth > document.documentElement.clientWidth

  // rootElem for quirksmode
  var rootElem = document.documentElement || document.body

  // Check overflow style property on body for fauxscrollbars
  var overflowStyle

  if (typeof rootElem.currentStyle !== 'undefined')
    overflowStyle = rootElem.currentStyle.overflow

  overflowStyle = overflowStyle || window.getComputedStyle(rootElem, '').overflow

    // Also need to check the Y axis overflow
  var overflowYStyle

  if (typeof rootElem.currentStyle !== 'undefined')
    overflowYStyle = rootElem.currentStyle.overflowY

  overflowYStyle = overflowYStyle || window.getComputedStyle(rootElem, '').overflowY

  var contentOverflows = rootElem.scrollHeight > rootElem.clientHeight
  var overflowShown    = /^(visible|auto)$/.test(overflowStyle) || /^(visible|auto)$/.test(overflowYStyle)
  var alwaysShowScroll = overflowStyle === 'scroll' || overflowYStyle === 'scroll'

  return (contentOverflows && overflowShown) || (alwaysShowScroll)
}
