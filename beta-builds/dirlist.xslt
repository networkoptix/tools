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
                <xsl:when test="contains($filePath, '-pdb')">
                    <td class="icon pdb"/>
                </xsl:when>
                <xsl:when test="contains($filePath, '.zip')">
                    <xsl:choose>
                        <xsl:when test="contains($filePath, 'client_update')">
                            <xsl:choose>
                                <xsl:when test="contains($filePath, '64')">
                                    <td class="icon client-x64"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <td class="icon client-x32"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:when test="contains($filePath, 'client_debug')">
                            <xsl:choose>
                                <xsl:when test="contains($filePath, '64')">
                                    <td class="icon client_debug-x64"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <td class="icon client_debug-x32"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:when test="contains($filePath, 'cloud_debug')">
                            <xsl:choose>
                                <xsl:when test="contains($filePath, '64')">
                                    <td class="icon cloud_debug-x64"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <td class="icon cloud_debug-x32"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:when test="contains($filePath, 'server_update')">
                            <xsl:choose>
                                <xsl:when test="contains($filePath, '64')">
                                    <td class="icon server-x64"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <td class="icon server-x32"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:when test="contains($filePath, 'server_debug')">
                            <xsl:choose>
                                <xsl:when test="contains($filePath, '64')">
                                    <td class="icon server_debug-x64"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <td class="icon server_debug-x32"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:otherwise>
                            <td class="icon"/>
                        </xsl:otherwise>
                    </xsl:choose>
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
    height: 24px;
    width: 24px;
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

.client-x64 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAEsSURBVEiJ7ZSxSwMxFIe/lzvQDoK6SjcHt7oLxS4Kii5S6Kb1X3Dp5OAunV1OHQTx0EFRcChXBHfHFtx0lYoOKtwlLodoPS/aG6TQD7Lk5fe+EJLAgP9GfrOoWKnmiXRdDHNxqqFwaoHvtTMLipVqXkJ9A4x3lTrGVYWrw927tLyyCYh0PaE5wJiEetsWtwo+jiWZ+cwCCya7QGikVC8zCxRODegklB5EhxuZBYHvtY2rCoAPPMXjSHQ43Tw5uLfl+5/UhzazvD7iDIULyqiSxkwKjAIYeFTIrRYdRG/uxfWp9/wnwezK2pQRswUsAcOWTb4CZ2Jks3m817IKSuXVRW3wgZylcTcvSigH/v7558lvt0gbdnpoDpCLs19IuqYTPTT/MZv1qxjQB7wD2YVU+59jWmcAAAAASUVORK5CYII=') no-repeat;
    }

.client-x32 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsQK/wvep0AAAHDSURBVEjH7dM/SNVRHAXwz73vQRlZYYukRoNETbkHpmv/MEoqCDST1oiWpoimhqDBKUNJogL/RBQ1BKEOhS3RWBCBYShEGApW9PzdFhWR8D1fNBQduHAv955zvny/5/KHEcpindEhOIlxmfPyNspcQ7WkS48H5RuctVlmUtIk6JLcFuxElWBIck9Updsc5Muof06yG/WokIyJXpk3JYgCCnKLj2Mpio0nTtc1trYNgm4/9BgXVWODaLubXsjZKniKU3rNLnLzpYiHQvYaVaBTLa6q0e6jBslBHaYld0Utur1czi/eovns+pI41Joyoc6E99gkc0R0DtUyYzoRbdNtsqQh7zvWNoPKxfPoYF9wWfTBDnxa3o6yYrrSYMmkRORL+CnPJC0rTNPCtn90sO/4avSiKYpyFzH9i6vPIStcKM4vguGB3rcpH/dgADMLqz9khYaR+3cm/PNYNQ17D3dU5tYV9scUmzOpPrAFEl+i8C4L2fD89/yT5w97Z9dk0HS0fVcK6QoOYX2RIr/hUUjh0sjQrTdFDZpb2w5kyQAq1tiNrzFoHR7oe7xqirLkRhniULHALRrTmt+Yac2a/8F//P34Cby8iV3rfs9bAAAAAElFTkSuQmCC') no-repeat;
    }

.client_debug-x64 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsEITJURNYAAALvSURBVEjH7ZRPaFRXFMZ/5743SSTptBMzM5k/tp1hKrqQ0A4UxTLGVlrsn4DY0FioNi50VRUsxKYb/6BIqc2mpYjF6kKwTAsVmq4qklIotNSKi6IgppLEabRNdMDiZN67p5tJipPRjHHhxgOPB/ee7557z3e+Dx7Fww6pJynX07sI3w6I8nIFddrg7DqTP3rxgQvkenoXiWfPAa1VW5Pqmo4fT345ci+8mfP6vh2ocThASDx7aC74nAVm2lI7XpkL786HuKGvj0u9uaaOMThdazkVDx9LJ8PPAKTj0TWpeGTvvAoYnF3AZI3pGMKjPx0PPWnV7lFfvp9XgTP5oxfVNR1AHihWPnwrC9SwQdW9YmCZcWiZtw6qIx2NLlNjz1ZxOFl2ShlWUBrNF2/VzwHA7kpe5W8duzpJg9tNiBdoYYuGeZrGkOs3Pj+aL97KrM001nXuyq7Nj+W6N74FkGlvDwNoNhv4Kb781NXEKvtnIqfZWEzzbR36TVuHDkaeG5rGLo7H2+46pp3r312ionvBfwOVJuArK/7xVCz874VC0+20uF0T6tEizgzmBj5BS+679md/eE9GA56Wfwd2zGrR6u5Nr6noWaAbaJpev1y4/voaefz8E+K+PcYUffzvEB7wmfs3viglT1/KSvOxy4XrO2pyYJXDwIIaorL7JOF5qMQI8IWk7lDrB14UVcFH2eZFlt5LyYlZoopFDoOuH9Qb3hVKhHDpkYWzgKecmzxlA0SlvD0VC29WkY/qsorhwrWtwNZXk0v7fOWgQdCqHAXW+UEMQoymQ8OFP/prvuBuPpOFwE5/LPixSdgxpky/HeGISc9wcCDwFx96UVxE98voSEVjauoV10QsPPgzxeRN7JEkDXxu7uSgrxzBUSEg5tsLMtWVioc/vS83dUr+m5cmJopL6HQKiWv/NGPeL6EN0/vNGA05DSc6x399ByDT2hq8H6uQSptnYiT5YgJbXvuJjveus8HfFDOwavyX4Wrgf4Xx/kNZv4oGAAAAAElFTkSuQmCC') no-repeat;
    }

.client_debug-x32 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsRAT6PggoAAANuSURBVEjHtZVfaFxFFMZ/M/du/ph066bZ7N/W7rKW5qFEXRBFSVLtS7UGQ7vYipo2lvZJW1GIxpdaUYpU+1BFmtjSIiqyLbTQ+CCKBESrYhQfpIIkxmzcpNGkXWlws/fO8SW7tEmqm0UPXIaZOd85d86Z7xv4n01VhHqSbhQ7gFEMz2BTj+EwEEQ4ynHOVp5gDysxZBHaURxFeBfFOqABxRmED9A00McsgF3B/88iNAMJoBbhApohXCZQaBTgYBWddTkRW7fvWt2a6joNQB8FjjOKJgjchGYN/XyBxSoUHwOPcYI/i1i7nODKMd8DDQDsJgocIsJOxrkNYQvdzCC8j+Zh+vjqWvy/l8g1R0rBAaJMkGE1GYYBL4ZONPuAIIYL7AY0YfrIltXktm1dOWBFcT54+pTiAJpfWQtMXVuOiq7pwgSlJGWaLoMpny61HAv7T8aj/lsB4uHApli46WBFCTTW88DMEkcfxKE3HvatMWJeEld9VFGCz9InfhJbtwBpIDf/4RpVK5odIvaohg3aov4/k4p4ILBBtBlacAtnClY+wd3kM+nc1WURjQPzfvOjsczGKFV2Ch/3Us8e8bOWap/tVt+ZSeeuJjYnqsuKe09H94rW1BOPACSCQT+AJJOez8N3nfst0mZ+ibRKMhSSdGOLnGlskYGmOwaL2HXhcOMNida+ded6UXIQ3IcQVQN8aJR7Khbyz17M1vwVV3bHtDjUq5LkcBkXr6H1fPD2T55SGY8jhe+A/YtKtDHV9aAoGQJSQE1xfTg7tWWTWvnDzcp+dJw5ehgrYRzgLft3XCXkHbk/qepODmen9i/ZAyMcA2qXIJV5WUUcB1EhPLyjYtfpzQtOABGFi/C009T8T1oUWUSqUNMxkK0DctkZJY8Pm+1q1SLgOesKtxgPAVXYFwv5u0Wp18p6D0ayl/YCex+INve4wiGNQhb4CNDpetEoQtS8PpL9sXfJE9xIZ5LgedYd9x7WETPOnO41Y/TreKkHr3omeNEJYKPkFZUZm+eY6HLJNR3yD3xJLnoF0x+lirf19T3oKTRhicKj9NmLaq4jFva/uawn08q7236ens6tp93KRi79UYd+Lo9UFffr0OKzqt5rn/zmcYBEQ4N3OVKh5stcsrHofRFMYfMbMrmr03i/FfSRtsmvRxYC/waGZywKaMOoRwAAAABJRU5ErkJggg==') no-repeat;
    }

.server-x64 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABrSURBVEiJY2AYBaOAUsCITdA+JL6NgYGhmIGBgY1Ic34xMDD2HFyzoBpdggmHhlxGxr/af/8zKxNpARsDw/9cbBIs2NUzTvr/n/kqM+Nfon3A+J9hEpFqqQtG4wAGRuOAIBjGcTAKRgHlAABPtzaLkG0fhQAAAABJRU5ErkJggg==') no-repeat;
    }

.server-x32 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsPLzYYsBoAAAFMSURBVEjH7dGxS5VRGMfxz3Pey4UiDGyRkiiUIFq0f8D+gxBsCALBok0iGl1canJScLjipWhouUFz0uASTW2NBYZg0NYFh/J9T0uiyE3vvREN3e94znOe73OeH3+Z6OvVXXPCbWypPFRzRmUJI7IV6171L7jvrMqO7IawInsuXMGw8FL2QjKsYRdqfcy/K7uKcZySvZO8V/oiJIE9xX5x6rl9ww/rtiQjOC25aM1bhXPCa9zR1N4vL3oW3DPqulWjHmu7gAkTvgktyS1rNk4MeWpm9gkeoX74fLP1LCyq2fYGlzGkMi15gJsO9nJew85xgnZEOblX1asiyo8dJMlnl/D18Do68ZsMYjnn4sPR5r/k2aJK0ydN7amZ2exf0lMGx/CdWNpsPV3ockXmI8prZS7GuhTUyfOdLmonZND1DyJbHmTwn2YwYMCf8xOG7HIDS59MkAAAAABJRU5ErkJggg==') no-repeat;
    }

.server_debug-x64 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsAI7g24P4AAAKSSURBVEjH7ZRPSFRRFMa/c9+bURmbUnvz5zlRM5lE4SJmFYQj6UYSIXRRQUjtLcHIskVUWFFRGEVEG2fRJmZRkBDRZhYRGREEgeS/xD9vxrFBXUQz8949LcohddQZa+m3urxz7vv47u+eC2xqU/8qyvUx1Np2HUAnAHue/0kDdCca6bu0vCBW2dBOZO23WNmdp4Ed4PZcBXWVYPeZlS8KWasmiEbC9CctL67/q/y61hfwaXsAIKC7G/y662reCdZjEI2EiYAoTHQH9LLLkuUVSNGZq3fDDCxJJSxwnFkdF0CNUFBagEGWwUiuasDtrhHEvWAUAQADW5jlM5/PWZ7XNV1Pu3TtzA629x6EAwYy2McleE0LGEOq8ZuReFUwg2gkTFUejzYciyU4GLS9NWz1AVHEaTC1yCE0m05UowLFQrl4BL8NqnV9+9fp6Vl1LQamtMvFY5Jkhf1e7cegUfwzQGpzkk2UkpLdMAcLTonal54Db9pp0mZy5hOAjrwYhFrbmkaNRFMDbf28jdQTU0ijCxPZbhPAQ3UWFjFSJtcHydE3aiQ6CmYQqwx1Z8A9BEABIQVGixzChYwra6QA8Iii27UzA+fXmORlQ+V1PQa4pZ/nzHGkUAYVx6hiRd8LZR47pQ1uypz1e7XTTHSroASGr7bLYtwUf4Kn/0rAABgMAYJXKb5xKP6+e61BW6EgYOu0ppwCkFNIo02OLGFwzRYDE6AScQ9NTiwef94GSa/W/w4LvnnIJz7Y8Uj4l9z1rowLChNsJJ4PUrrZr2sP8mYAAErKah1OJhf2ok4xKme+OyDOpcDZt8oBwWWK/Wld/MNJAKgqL3dueJIBYMJ3uBIy03iX46eOSudHhrgXig+MLe/7BSOq/KGNFcVBAAAAAElFTkSuQmCC') no-repeat;
    }

.server_debug-x32 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsPEm5w/AsAAAMxSURBVEjHtZZdaFxFGIafb87ZTWLi1mzcZHezaneNwR8KrbkSJBtsb4olUhLBihKs4l1tJWI0N1YlKipKrT+Y0NAgIkiEChak1Ytc+FdRQRCKbVNjkp5Nt4Y2geDunjOfFzbptqY1G9q5PLwz73zvc+abgWs8ZFWzHmc7wjZgAsvTuNRheROIo+xlHwdWb/Aka7B4KB0Ie1E+QmgFogifoXyCIcogCwDuKva/gHIH0ALUoHyP4WcCcggGAXycRbGpePlBSuxjAkMcuA7DzQzxLQ4NCIeARxhmflHuVGzwBCnu5n1SDDBPM7Ce9cwhjGJ4kCEO/y/kbHfPK0AvEC7/PjY6IuzGZYqvgTQQwbIVw07gAS7kkmQQ70oG8yLBBt+GrSPBiWVMDH+yFsiXx7HcuAwDeUfV+e3Sxc+bK7uxDDPOMPPZ7h69JgconYztz6RitwFkkk2b0snGl5bTuZUwKI9JYAyf/kyy/gWr9kWs6a0gInaIBHcF6tx6uQoCKzVq2KbqThhYZxzqrgoDgExT0zojugelCkDhelX7aSoViV6VXrQ2GXvqJg3vuYdaPErcqTUckjlOUtj8h5f/smIGY6Mj0hKPx47ncnltawt944U2ZkyVFlHpssfo9CO00kC1cZ6/n38NWpPJG38/deqMeyUG5efASjCSTsQWjnrVf2fE7ZxVnzq50AjOEhCxtH8R3/DVDpkK+Vr6Bdi1IgbZ7p4t415+yyZZ8+sN4j48TZE+JpfUPvCee4ZAlIKvG9ukdv+4l99VMYNcc7a/hA4I4CAUULrsMZ4rNS4ZOUDcVL3RfvrIsytu1+lE44egXQf1rD9BgXpcHpKG/+g+d85xiw3RJKWd6URsu4q8XlEFXqq9L1BeM+cLL5ZVoICiGISEU/3qvTM/9Fd0H7RBqDeYjhiw0xTpsScuYvByKIcKuCI6IFOTi/Gv2GA2ETv4HXOpc9ihFGE+MOmL/vW+UiOOCiExB45KsTOdjL1b0ZXpFILu47Ozc7fT4XjNp/+qxTxTQJd6VS1G653wxx0zPz4K0BKNRlb/qgAmU/c1Y0ub39KZx7bayE+KeTs7c+Tkpbp/AN1RNKVBPSCBAAAAAElFTkSuQmCC') no-repeat;
    }

.cloud_debug-x64 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsGFrjfg1sAAAPJSURBVEjH7ZVdbNNlFIef8/7bDdiobKzbWirYOcmIEpEJxjjWIsTEREhkXQwEV3YzEqOGKAaZXoDgR0yUGCVo/NqGH4GtoglIMAYoUYkfmOAFoCgIcxkTbcYMxK79v8ebrjCFUeOt5/Z3znlyPt7zwv92FZNCnBrua5nuyTIXTKkV/cMR55t93W99/58BjUvijRh5XtDbLhP5rbG2fV9i656xcjhXEiLN8TYRtglMBfqAXcBuUY4hVAB1KrI8PGOW9+ejh/f+qwoiTfGlCO8BWUEeG39+4pbdu19Oj+jRaNRjJ09bKcILQDHKI8lE56aCAPOaW/1G7RGgQpGmAz0dH1yxhc3xxaLsANKuaN1n3V2nxxxIY6xlZSQW74/E4hqJxbsLGWKkqaVrLN3ky26KbxTkVaAS2Kkq7WMFhoP+jpqQ/4ZkoqulJli1MBysfAogEovvmdfc6h8FmL8kfocKTwDnBVmQ7OlcdCDRcfwq65ckS3tNsGyqVbteXfk4J91l1H4SXbFiXB5gHVYDiMjG/T0d+wtpjWtlvBqWqnpOGZhpHEpz0mlglp7noYststQDGNd5v5DkNVVVM43oSyjFAAoTVe32UMhXntHBZQCoLr8IEPwAxnEGL5txXc5v3UjFdn6IIk8zZTRQSpv6uY7iMo9bPPeLxEefq1qSPZ03XwQoJwEyDM+9AsDWVlf7WYfV+nrvO1y/YJup1QdMNUf4k9qslwczk9nsXrsW4EBiq0wPBivyABUSubKeqW9r816OYcXtDAf8Pcf6x71dI8WLU5od9YYGcblg3cad1bd8Gg74k1nNPJkHZMSzKXcObi1NpZPzlrTOjkajnksTnOg/e89Cuea7SeJZ1scwa+jNa1lgs+c3XFHSWV1QLyUdJ/rPrsoDDna/mVLVRcAAcLsx9pBWTMtEYnG9tIgNMiWbRSWAlzcknBc8wNpsFaqCi/JwtnLGP47dqaOHz0y9cXanoB6gGvAB5tSRw+vDgcrXyiZO6AjgnbOXodITpLlJJuAC2zVFgy0BYIdzjgtYhow75wcfqyb5Sgv7D0asP9S4xlWeM7mwYZQme5zHM5UooCgGIeCMe7Zh4Mv2UafialYP3kfdPp8B28cwcfvTqBls8J5BBTwi+rT80jtySAsGpAL+XQcZCp3Dvh6iiC1m9AzWZCpxVPCK+fCYDC8OB/2vjGgFmZN2Yz+mUkN1RJ3+Kb/+XoJZnUaLRvQSjJY5Re9GB76+H6C2vNxX8J+c87t0o+gN3TkFm7n7RR1ovdf6DilmU2Tgq5N/D/wLvgphlPpflwYAAAAASUVORK5CYII=') no-repeat;
    }

.cloud_debug-x32 {
    background: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+ECCQsRNR87dr8AAAQcSURBVEjHtZVdbJNlFMd/z/O2G7BR2KBb29VJ5yQSJSITEuNYiyMmJoDCuhgIrhuamRg/MGIQ9GIIKhdGYpCgw+E+ECKsiglKJGrYEvnQYIIXiKKQAUuZaIUZFre+73O8YOs2BTZIPLf/95zfe87J8z/wP4e6qazHWY5iCdCB4XlcZGN4E/AhbKKBPTcPqGUChgRCBMUmhBYUU4FcFHGEnWhyqacHwDWamqWPVk112cw+EG/eDvQgTAOKgbEIh9F8j8N5FBoF2FgDufp6hcsWx8rKotWHLUf9JEq1AFBPigY60PiAcWgK2cpBLCah2A8sYxt/DdS4ZgfhylgtwmYQF9AJtAPwBEFgAwVU08kMhPks50+EHWgeoZ4jIy45XBFbgmIHYCvUi2Mvj9+yb9+mXgDqcHGOr4AQ4MGwCM1zwMMMziVAPYmrAuZU1ni1mOPAZEFVtLc2fvyfP6hDc4YpwIWh4xgxyqJVT4ajsUQ4GpNwNLZ7NDnhiqrm6+npJUcqYusV6l0gD9grotZcLzEU8DYWBb23t8Wbq4oC+fNCgbxXAcLR2BdzKmu8wwBzF8fuF8XLwGWFKm9rbVrQHm88OcILbcNmTVEgp9CIWSuO+rxfelCL2R+prh6TBhiLlQBKqfUHWhsPjGY0jlFjRbNExNWhYbq2yO6XzgAz5DLPDI7IUAKgHWvnaIoX5edP10reRsgEEBgvYnYFg57clFxcCoDIskGAwgugLeviVSvW9X9XN9CxmRskw1VJDqVkUyteppCZ43IyZx+Mf/qNiKGttenuQYBwGiBF3+xrAEyxz+elDiMlJe7t3Fb+kS6Wp7SP4/xNse3m6dQkNju3rAZoj7eoqYHA5DRAFPH+tl4vqa11X41hlNMU8ntbTyTGfFCkMhcmxR72hi7i0GOcsr2+e74M+b1ttqReSQNSyrWx3w7uzU72ts1ZXDMzEokMs5FTiQvz56kJP0xUrqWd9LGKs2nNBja7fsdRQq8t5SUqq/FU4sKKNODQ7oakiCwAuoD7tDZHZfKtqXA0JkObWKcKbBtRfty8r0IMNbTVdj4iCgfhWTtv2oCWttWOH4+dL7xzZpO6Ym4+wAPojuPH1ob8ee/ljB/X6Mc962u6s0/Ry11qHA6wS5KUmiwAPrEu0YOhWzuzfvawYqIn+8YOTiJYtsoRNuj+tD6ECnOSl1J5CCAIGoXfGvNGadeRNSPeg6FRAu4XnE6PBtNJHzHz67AdrHOfRxS4lJLX1LmzA0Y6akDS7/3sEN3BS5itQTLYoofvYFUqD0sUbqX3nFB9C0MB7zujPpkAVq8T/SWZ7L6DiJUo+O2PLPTKXiRjQM9CS46V8WGk67vHAIpzcz03cvTVFUcYjLPBBwowqYfekq6aRcZzVNAbw13fnv534j/Lf3i6pNlXfQAAAABJRU5ErkJggg==') no-repeat;
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
                        <tbody>
                            <tr>
                                <td class="icon folder"/>
                                <td class="n">
                                    <a href="../">Parent Directory</a>/</td>
                                <td class="m">&nbsp;</td>
                                <td class="s">- &nbsp;</td>
                                <td class="t">Directory</td>
                            </tr>
                            <xsl:apply-templates select="list/directory">
                                <xsl:sort select="@mtime" order="descending"></xsl:sort>
                            </xsl:apply-templates>
                            <xsl:apply-templates select="list/file" />
                        </tbody>
                    </table>
                </div>
                <div class="foot">nginx</div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
