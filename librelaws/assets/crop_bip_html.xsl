<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:strip-space elements="dl dt dd" />
  <xsl:template match="/">
    <html>
      <meta charset="utf-8"/>
      <body>
      	<xsl:apply-templates select="//fieldset/fieldset/fieldset[h1][position() &lt; 3]" />
      </body>
    </html>
  </xsl:template>

  <!-- IdentityTransform -->
  <xsl:template match="@* | node()">
      <xsl:copy>
      	<xsl:apply-templates select="@href | node()" />
      </xsl:copy>
  </xsl:template>

  <!-- Drop surrounding fieldset -->
  <xsl:template match="fieldset">
    <xsl:apply-templates select="@href | node()" />
  </xsl:template>

  <!-- Drop comment nodes -->
  <xsl:template match="comment()">
  </xsl:template>
</xsl:stylesheet>
