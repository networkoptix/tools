<?xml version="1.0"?>
<!-- 
  dirlist.xslt - transform nginx's into lighttpd look-alike dirlistings

  I'm currently switching over completely from lighttpd to nginx. If you come
  up with a prettier stylesheet or other improvements, please tell me :)

-->
<!--
   Copyright (c) 2016 by Moritz Wilhelmy <mw@barfooze.de>
   All rights reserved
  
   Redistribution and use in source and binary forms, with or without
   modification, are permitted providing that the following conditions 
   are met:
   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
  
   THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
   IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
   ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
   DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
   OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
   HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
   STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
   IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
   POSSIBILITY OF SUCH DAMAGE.
-->
<!DOCTYPE fnord [<!ENTITY nbsp "&#160;">]>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/1999/xhtml" xmlns:func="http://exslt.org/functions" version="1.0" exclude-result-prefixes="xhtml" extension-element-prefixes="func">
    <xsl:output method="xml" version="1.0" encoding="UTF-8" doctype-public="-//W3C//DTD XHTML 1.1//EN" doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd" indent="no" media-type="application/xhtml+xml"/>
    <xsl:strip-space elements="*" />

    <xsl:template name="size">
        <!-- transform a size in bytes into a human readable representation -->
        <xsl:param name="bytes"/>
        <xsl:choose>
            <xsl:when test="$bytes &lt; 1000">
                <xsl:value-of select="$bytes" />B</xsl:when>
            <xsl:when test="$bytes &lt; 1048576">
                <xsl:value-of select="format-number($bytes div 1024, '0.0')" />K</xsl:when>
            <xsl:when test="$bytes &lt; 1073741824">
                <xsl:value-of select="format-number($bytes div 1048576, '0.0')" />M</xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="format-number(($bytes div 1073741824), '0.00')" />G</xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template name="timestamp">
        <!-- transform an ISO 8601 timestamp into a human readable representation -->
        <xsl:param name="iso-timestamp" />
        <xsl:value-of select="concat(substring($iso-timestamp, 0, 11), ' ', substring($iso-timestamp, 12, 5))" />
    </xsl:template>


    <xsl:template match="directory">
        <xsl:variable name="dirPath" select="."></xsl:variable>
        <tr>
            <xsl:choose>
                <xsl:when test="contains($dirPath, 'default')">
                    <td class="icon nx"/>
                </xsl:when>
                <xsl:when test="contains($dirPath, 'digitalwatchdog')">
                    <td class="icon dw"/>
                </xsl:when>
                <xsl:when test="contains($dirPath, 'vmsdemo')">
                    <td class="icon nx"/>
                </xsl:when>
                <xsl:otherwise>
                    <td class="icon folder"/>
                </xsl:otherwise>
            </xsl:choose>
            <td class="n">
                <a href="{current()}/">
                    <xsl:value-of select="."/>
                </a>/</td>
            <td class="m">
                <xsl:call-template name="timestamp">
                    <xsl:with-param name="iso-timestamp" select="@mtime" />
                </xsl:call-template>
            </td>
            <td class="s">- &nbsp;</td>
            <td class="t">Directory</td>
        </tr>
    </xsl:template>

    <xsl:template match="file">
        <xsl:variable name="filePath" select="."></xsl:variable>
        <tr>
            <xsl:choose>
                <xsl:when test="contains($filePath, '.exe')">
                    <td class="icon nx"/>
                </xsl:when>
                <xsl:when test="contains($filePath, '.msi')">
                    <td class="icon msi"/>
                </xsl:when>
                <xsl:when test="contains($filePath, '.pdb')">
                    <td class="icon pdb"/>
                </xsl:when>
                <xsl:otherwise>
                    <td class="icon"/>
                </xsl:otherwise>
            </xsl:choose>

            <td class="n">
                <a href="{current()}">
                    <xsl:value-of select="." />
                </a>
            </td>
            <td class="m">
                <xsl:call-template name="timestamp">
                    <xsl:with-param name="iso-timestamp" select="@mtime" />
                </xsl:call-template>
            </td>
            <td class="s">
                <xsl:call-template name="size">
                    <xsl:with-param name="bytes" select="@size" />
                </xsl:call-template>
            </td>
            <td class="t">File</td>
        </tr>
    </xsl:template>

    <xsl:template match="/">
        <html>
            <head>
                <style type="text/css">a, a:active {text-decoration: none; color: blue;}
a:visited {color: #48468F;}
a:hover, a:focus {text-decoration: underline; color: red;}
body {background-color: #F5F5F5;}
h2 {margin-bottom: 12px;}
table {margin-left: 12px;}
th, td { font: 90% monospace; text-align: left;}
th { font-weight: bold; padding-right: 14px; padding-bottom: 3px;}
td {padding-right: 14px;}
td.s, th.s {text-align: right;}
div.list { background-color: white; border-top: 1px solid #646464; border-bottom: 1px solid #646464; padding-top: 10px; padding-bottom: 14px;}
div.foot { font: 90% monospace; color: #787878; padding-top: 4px;}

.icon { 
    height: 16px;
    width: 16px;
    padding-bottom: 1px;
    padding-top: 1px;
}

.folder { 
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAACxEAAAsRAX9kX5EAAAAYdEVYdFNvZnR3YXJlAHBhaW50Lm5ldCA0LjAuOWwzfk4AAAJMSURBVDhPfZJZTxNRAEb5b0oMGokhpg9CAa0bUaEBN0xQUCNUAzG+EGPiiylR00BBwqJIV0pb2lKg63RhBrpRxkKHabGl+DlcwpAL0YdzX745ZzKTWwWg6jc/jEJ6AGKiHwKrQT7eh3xMg63IK+TCL8AHu5H1d2Ez/AZCxiApIN4B5Cik+7FXHMX+3gbE7Hv8Wu1F1N2JcmEG+2WzTEmcQMbf+4/A7jgBqBDYhRb4bc9QzA2jUjJI2w+UxUkk3O3S/p/AYQSI2a9jyfgYyeUeIpaEUexu6bDmUh/MJwKpk4EKGGsTvLP3sb7YRcQCr8XOxkdwzlZpPxHYSb6W5VJBjz/7IoLGK/DMtIJzPSSikBzE9tpbrDrunA4I632yvJv/iko5A99PBdzTt8E61ETMxTXgmefSJ7QhG9XKEXJssy9lWeQ/oZi3Yfl7HRYmriJuayFiNvgEmZUOpLz3EJ27QQdy8R5Z3k5/AM+9g3eyFo6xekTNKllMuG+C53lELCo6wEe6KDkT0cAzfh72kctgDA1EXHc2g5uvJwHGfI0ObIQ6KTnh64Zr7BxsulqEZxREZOcUWLXUkUDY1EwH0r4HlMx6HsGpr4b1Sw1C0r84EOOmWoJyOoaQsZEOJJbUlBxztME5chbWz9UITh2KR9RoVxA0KOkA57lLyYz1FglYhs6cCsRMlxCd76ADqcAAwpYmBIxKBAyNEs0kYBq6AN+UQrpUjeStgdkGSW7HJkuu+3HgiE1uCoz9KVzfLsKqVyGyqENRSErT8TM0qPoLtCMvemXNEccAAAAASUVORK5CYII=') no-repeat;
    }

.msi { 
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAACxEAAAsRAX9kX5EAAAAYdEVYdFNvZnR3YXJlAHBhaW50Lm5ldCA0LjAuOWwzfk4AAADBSURBVDhPjZDREcMgDEO9EzsxCjt0GwboP+O4yCBiKCFxTj6QrZdcRFW3SilpKeVWmIvIPgxhIcavho1QrwHYj9Uw1XP4PAAwoAxQTR+WEwAmawK4cIDR5wOAi1fO+QIs4b9/gAOLYQJ43mkAam58AQy/cBJ2JgDKA2y46DUAdxs01zqK8+kl8D2AYVtorvUp1IXhAHDIMwFc9gDY1BFArz1MoLsr2h0AZX596D0CCGE1UP+KJQy11oN+wXsUZ5dUfquDqPUgD9jhAAAAAElFTkSuQmCC') no-repeat;
    }

.pdb { 
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAYdEVYdFNvZnR3YXJlAHBhaW50Lm5ldCA0LjAuOWwzfk4AAAIaSURBVDhPjZLLTxNRFMb757Agogvd6MK48y8gsNLg+xUTXTSkC4wskMZgg2AFtQZJa0HbpinFqhULGtqUdHgUrEWoVVKGSWxp6fQxHebzzB2UYtLak5w592a+73fPfegA6OLJDCJLCcyEv8I3E4XrbQQ2dxCW8QAGR/0YsvlJBqb9N9knwG2hqXUShy8t48TtDZzq3MRxquq8qdWLHrObZHUA/rkUms+EmKnNKODqoID2XoHBms+G0D3gJFkdgOfTD7Sc42hlnpmNYxpEnR86z6HL9IpkdQD29wlaKcg6UFe+MiCgraoDw/2XJKsDeDbxje31yMX9M1CrezrG0jEV/VvtbyKs/hkzgNM3hy/JApbWRXDxPPxhHq6pNWaqFYqi4OjpDuhCkRXYPLMwW73oGx6HwTiE64Y+XKN0fogyMeuT4qQ+hWM31tFyYRElaQ9gmwhi1PUZUkXBMN33ZrqMfosX8Y0i7D5Oc1aFLCsolHeRzcv7AHlXwd2Hr7GwJkJ/b4TVW91P8cI9u2fToroD/pekAZ47AjBZPOh97EDXAyv0PRbcvGPG5U4TntBLVEPdr9qhWJSRzlWQInMiVdIA9L9mPrK+IzMNaLZTkA90sJwo/B/QPzKJUllBVpQhbEv4KZSxSmezSLcVju00BtjOV7CVkZDkSwc6mF7INQbg0xK+kzmWLGJ+VURwJYeP81n4wpnGAKqodnbgN9+QCThpLtD8AAAAAElFTkSuQmCC') no-repeat;
    }

.nx { 
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABG0lEQVQ4y2PQtrCfDcR/gPg/iRikZz6Dqr7pP0Ut/f/kYJBeBqIU6xj910hq+K/bt++/spXbf63SWf+VDC3BcgzE22jwX7txDVDz7P+KeqZwcQZSnKwWmP5fd9IRuO0YBpjbO//XM7f+b2hp9z8qIeW/kZUdXE7J0OK/enz1f43kxv9axTNQDVDWMfzfM3Hy/79///6fNH3m//Wbtvw/c+78/7dv3/03tnEAOxmkSdnK/b+Sqf1/vWmn/qsFZ6G6QN/c5j8I1Le0g/maRmb/f/78+T+3uAyvt+AGgJwOAkmZOXDJT58+/69pah3qBtQ2E2lAR28/2ICVa9aBoy+vpALM33/o8H8zO2fCBpCLQQb8o9SA+WQaAtKzCACtBb3bG9yHzwAAAABJRU5ErkJggg==') no-repeat;
    }

.dw { 
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACEElEQVQ4y22STUuUcRTFz7n/Z16c8RknGc0XVOiFVAzbFJS56wPUTkJaVJu+Q5+hTZuoVdC+L9HCDCKQoFIpB3Uy5kUdnXHmmed/WjhJomd1OFy4l3N/9N5DAgQQBARAIEmTPHTag5SE8ySJ5NmcPmr78i902jDHsKDDGtpHzBXYN6Tatupl5gaYH9ZuSfUKkml2aqXmiwe+vAEzNz6rqBmvLiXnH/U8edV4uRB9ep+4vZB59rb55mn7w7tg5p7xWGaQfOm7ZfIMkn63pKjly0XrCVXeUCfyuzsEbeiqAYA5tRru0s3E3UXFEVNZ1Stx6YcOKgrSqpf9zpoOq3DOjU4bAJDwHcvmU/efMzeIRBrNvXhtCe0mM6Fah/H6Mpr7SGZsdMqOGyHNR0egMR0y3at2w68vC3DDk/JxvPZR7QbDgl28Yic1EoCZ9v+wt19RO976SnM2cYMu4Te+qNW0wgT7BrsnyXumMnFxJf75mWGBgKpbDJLu2hzTWV/bYqdlI1OkdTewJxcXV45eP1ZzX1EL6SxApEM3PstwADSYc2Mzkkze67Cmxp5+r/rtb5B3YzOQVN1EkGBugGFB1U1FRzY6TTJgKpOYW9RBBUGK2XwwOW+XbzHb7ytFN36dUuLOQ+aHmLlgI5MAzmNJwj+KzhIVSEKXRHR/QoOPu5ya07EHYI5kAAA08GSekv5PTnngL96EEdx8DtahAAAAAElFTkSuQmCC') no-repeat;
    }

                </style>
                <title>Index of <xsl:value-of select="$path"/>
                </title>
            </head>
            <body>
                <h2>Index of <xsl:value-of select="$path"/>
                </h2>
                <div class="list">
                    <table summary="Directory Listing" cellpadding="0" cellspacing="0">
                        <thead>
                            <tr>
                                <th class="icon"/>
                                <th class="n">Name</th>
                                <th class="m">Last Modified</th>
                                <th class="s">Size</th>
                                <th class="t">Type</th>
                            </tr>
                        </thead>
                        <!-- uncomment the following block to enable totals -->
                        <!--
            <tfoot>
              <tr>
                <td>&nbsp;</td>
              </tr>
              <tr>
                <td colspan="4">
                  <xsl:value-of select="count(//directory)"/> directories,
                  <xsl:value-of select="count(//file)"/> files,
                  <xsl:call-template name="size"><xsl:with-param name="bytes" select="sum(//file/@size)" /></xsl:call-template> total
                </td>
              </tr>
            </tfoot>
            -->
                        <tbody>
                            <tr>
                                <td class="icon folder"/>
                                <td class="n">
                                    <a href="../">Parent Directory</a>/</td>
                                <td class="m">&nbsp;</td>
                                <td class="s">- &nbsp;</td>
                                <td class="t">Directory</td>
                            </tr>
                            <xsl:apply-templates />
                        </tbody>
                    </table>
                </div>
                <div class="foot">nginx</div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
