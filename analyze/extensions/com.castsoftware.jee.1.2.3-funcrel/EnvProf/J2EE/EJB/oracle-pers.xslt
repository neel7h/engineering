<?xml version="1.0" encoding="UTF-8"?>
<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:template match="/">
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
				<xsl:for-each select="oracle-descriptor/persistence-descriptor[psi-ri]">
					<xsl:element name="entity">
						<xsl:element name="entity-name">
							<xsl:value-of select="ejb-name"/>
						</xsl:element>
						<xsl:element name="tables">
							<xsl:for-each select="psi-ri">
								<xsl:element name="table">
									<xsl:element name="schema">
										<xsl:value-of select="schema"/>
									</xsl:element>
									<xsl:element name="table-name">
										<xsl:value-of select=" table"/>
									</xsl:element>
									<xsl:for-each select="attr-mapping ">
										<xsl:element name="column">
											<xsl:attribute name="name"><xsl:value-of select="column-name"/></xsl:attribute>
											<xsl:attribute name="java-field"><xsl:value-of select="field-name"/></xsl:attribute>
										</xsl:element>
									</xsl:for-each>
								</xsl:element>
							</xsl:for-each>
						</xsl:element>
					</xsl:element>
				</xsl:for-each>
			</xsl:element>
		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
