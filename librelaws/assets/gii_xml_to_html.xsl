<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:template match="/dokumente">
    <html>
      <meta charset="utf-8"/>
      <body>
      	<xsl:apply-templates select="@* | node()" />
      </body>
    </html>
  </xsl:template>

  <!-- IdentityTransform -->
  <xsl:template match="@* | node()">
      <xsl:copy>
      	<xsl:apply-templates select="@* | node()" />
      </xsl:copy>
  </xsl:template>

  <!-- Incomplete! Throws away things! -->
  <xsl:template match="norm/metadaten">
    <h1>
      <!-- Main title; only in first node has langue -->
      <xsl:choose>
        <xsl:when test="langue">
	  <xsl:value-of select="langue" />
	  <xsl:text> </xsl:text>
	  (<xsl:value-of select="amtabk" />)
	</xsl:when>
      </xsl:choose>
    </h1>
    <dl>
      <xsl:for-each select="standangabe">
	<dt><xsl:value-of select="standtyp" /></dt>
	<dd><xsl:value-of select="standkommentar" /></dd>
      </xsl:for-each>
    </dl>
    <h2>
      <xsl:value-of select="gliederungseinheit/gliederungsbez" />
      <xsl:text> </xsl:text>
      <xsl:value-of select="gliederungseinheit/gliederungstitel" />
    </h2>
    <h3>
      <xsl:value-of select="enbez" />
      <xsl:text> </xsl:text>
      <xsl:value-of select="titel" />
    </h3>
  </xsl:template>

  <!-- Remove table related cruff -->
  <xsl:template match="tgroup | colspec">
    <xsl:apply-templates select="node()" />
  </xsl:template>
  <xsl:template match="row">
    <tr>
      <xsl:apply-templates select="@* | node()" />
    </tr>
  </xsl:template>
  <xsl:template match="row/entry">
    <td>
      <xsl:apply-templates select="@* | node()" />
    </td>
  </xsl:template>
</xsl:stylesheet>
