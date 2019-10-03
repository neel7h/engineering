<?xml version="1.0" encoding="UTF-8"?>
<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:variable name="sModuleDir" select="document('module-dir.xml')/module-dir/@path"/>

  <!-- Mapxmi Processing -->
  <xsl:template match="/">
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
        <xsl:apply-templates select="*[local-name() = 'EjbRdbDocumentRoot']/nested[@*[local-name() = 'type'] = 'ejbrdbmapping:RDBEjbMapper']" />
			</xsl:element>
		</xsl:element>
	</xsl:template>

  <!-- Entity Processing -->
  <xsl:template match="nested[@*[local-name() = 'type'] = 'ejbrdbmapping:RDBEjbMapper']">
    <xsl:element name="entity">
      <xsl:element name="entity-name">
        <xsl:variable name="beanRef" select="outputs/@href"/>
        <xsl:variable name="beanId" select="substring-after($beanRef, '#')"/>
        <xsl:variable name="RelEjbJarFile" select="substring-before($beanRef, '#')"/>
        <xsl:value-of select="document(concat(string($sModuleDir), '/', string($RelEjbJarFile) ))/*[local-name() = 'ejb-jar']/*[local-name() = 'enterprise-beans']/*[local-name() = 'entity'][@id = $beanId]/*[local-name() = 'ejb-name']"/>
      </xsl:element>
      <xsl:element name="tables">
        <xsl:apply-templates select="inputs[@*[local-name() = 'type'] = 'RDBSchema:RDBTable']" />
      </xsl:element>
    </xsl:element>
  </xsl:template>


  <!-- Tblxmi or Dbxmi Processing -->
  <xsl:template match="inputs[@*[local-name() = 'type'] = 'RDBSchema:RDBTable']">
    <xsl:element name="table">
      <xsl:variable name="TableRef" select="@href"/>
      <xsl:variable name="TableId" select="substring-after($TableRef, '#')"/>
      <xsl:variable name="RelFilePath" select="substring-before($TableRef, '#')"/>

  		<!-- use descendant xpath axe since the referenced file could be a Tblxmi or Dbxmi mapping file -->
      <xsl:variable name="TblNode" select="document(concat(string($sModuleDir), '/', string($RelFilePath) ))/descendant::*[local-name() = 'RDBTable'][@*[local-name() = 'id'] = $TableId]"/>
      <xsl:element name="table-name">
        <xsl:value-of select="$TblNode/@name"/>
      </xsl:element>

      <!-- Columns -->
      <xsl:apply-templates select="$TblNode/columns" />
    </xsl:element>
  </xsl:template>

  
  <!-- Column processing -->
  <xsl:template match="columns[@*[local-name() = 'type'] = 'RDBSchema:RDBColumn']">
    <xsl:element name="column">
      <xsl:attribute name="name"> <xsl:value-of select="@name"/> </xsl:attribute>
    </xsl:element>
  </xsl:template>
</xsl:stylesheet>
