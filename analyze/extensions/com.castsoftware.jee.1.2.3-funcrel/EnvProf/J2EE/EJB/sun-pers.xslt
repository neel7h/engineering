<?xml version="1.0" encoding="UTF-8"?>
<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:template match="/">
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
				<xsl:for-each select="sun-cmp-mappings/sun-cmp-mapping/entity-mapping">
					<xsl:element name="entity">
						<xsl:element name="entity-name">
							<xsl:value-of select="ejb-name"/>
						</xsl:element>
						<xsl:element name="tables">
							<xsl:element name="table">
								<xsl:element name="table-name">
									<xsl:value-of select="table-name"/>
								</xsl:element>
								<xsl:for-each select="cmp-field-mapping ">
									<xsl:element name="column">
										<xsl:attribute name="name">
                      <!-- might be TABLE.COLUMN -->
                      <xsl:variable name="ColName" select="substring-after(column-name, concat(table-name, '.'))"/>
                      <xsl:if test="$ColName != ''">
                        <xsl:value-of select="$ColName"/>
                      </xsl:if>
                      <xsl:if test="$ColName = ''">
                        <xsl:value-of select="column-name"/>
                      </xsl:if>
										</xsl:attribute>
										<xsl:attribute name="java-field">
											<xsl:value-of select="field-name"/>
										</xsl:attribute>
									</xsl:element>
								</xsl:for-each>
							</xsl:element>
						</xsl:element>
					</xsl:element>
				</xsl:for-each>
			</xsl:element>
		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
