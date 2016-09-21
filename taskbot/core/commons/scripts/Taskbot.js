// Most common scripts
var LOADED_SCRIPTS = {};
var LOADED_STYLES = {};

// aka include
function loadScript(url, callback)
{
  if (LOADED_SCRIPTS[url]) return; // already loaded
  // Adding the script tag to the head
  var head = document.getElementsByTagName('head')[0];
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = url;

  // Then bind the event to the callback function.
  // There are several events for cross browser compatibility.
  if (callback)
  {
    script.onreadystatechange = callback;
    script.onload = callback;
  }

  // Fire the loading
  head.appendChild(script);
  LOADED_SCRIPTS[url] = true;
};

function loadStyle(url, type, callback)
{
  if (LOADED_STYLES[url]) return; // already loaded
  // Adding the script tag to the head
  var head = document.getElementsByTagName('head')[0];
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.type = 'text/css';
  link.href = url;
  link.media = 'all';

  // Then bind the event to the callback function.
  // There are several events for cross browser compatibility.
  if (callback)
  {
    link.onreadystatechange = callback;
    link.onload = callback;
  }
  
  // Fire the loading
  head.appendChild(link);
  LOADED_STYLES[url] = true;
}

// Add onload event
function addLoadEvent(func)
{
  var oldonload = window.onload;
  if (typeof window.onload != 'function')
  {
   window.onload = func;
  }
  else
  {
    window.onload = function() {
      if (oldonload)
      {
        oldonload();
      }
      func();
    }
  }
}

function getReportId ()
{
  var regex = new RegExp( "[\\?&]report=([^&#]*)" );
  var results = regex.exec( window.location.href );
  if( results == null )
    return ;
  else
    return results[1];
};
