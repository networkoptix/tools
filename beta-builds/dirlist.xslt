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
        <tr>
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
        <tr>
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
div.foot { font: 90% monospace; color: #787878; padding-top: 4px;}</style>
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
