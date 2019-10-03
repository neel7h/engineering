<?xml version="1.0" encoding="UTF-8"?>
<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:template match="/">
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
				<xsl:for-each select="ejb-jar/enterprise-beans/entity">
					<xsl:element name="entity">
						<xsl:element name="entity-name">
							<xsl:value-of select="ejb-name"/>
						</xsl:element>
						<xsl:element name="tables">
							<xsl:for-each select="cmp2-info">
								<xsl:element name="table">
									<xsl:variable name="tablName" select="table-name"/>
									<xsl:element name="table-name">
										<xsl:value-of select="table-name"/>
									</xsl:element>
									<xsl:for-each select="cmp-field">
										<xsl:if test="count(descendant::*[local-name() = 'column-name']) > 0">
											<xsl:variable name="colNam" select="descendant::*[local-name() = 'column-name']"/>
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="/ejb-jar/table-properties[table-name = $tablName]/column-properties[column-name = $colNam]/column-name"/></xsl:attribute>
												<xsl:attribute name="java-field"/>
											</xsl:element>
										</xsl:if>
										<xsl:if test="count(descendant::*[local-name() = 'column-name']) = 0">
											<xsl:variable name="colNam" select="field-name"/>
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="/ejb-jar/table-properties[table-name = $tablName]/column-properties[column-name = $colNam]/column-name"/></xsl:attribute>
												<xsl:attribute name="java-field"/>
											</xsl:element>
										</xsl:if>
									</xsl:for-each>

								</xsl:element>
							</xsl:for-each>
							<xsl:for-each select="cmp-info/database-map">
								<xsl:element name="table">
									<xsl:element name="table-name">
										<xsl:value-of select="table"/>
									</xsl:element>
									<xsl:for-each select="column-map">
										<xsl:if test="count(descendant::*[local-name() = 'column-name']) > 0">
											<xsl:variable name="colNam" select="descendant::*[local-name() = 'column-name']"/>
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="$colNam"/></xsl:attribute>
												<xsl:attribute name="java-field"/>
											</xsl:element>
										</xsl:if>
										<xsl:if test="count(descendant::*[local-name() = 'column-name']) = 0">
											<xsl:variable name="colNam" select="field-name"/>
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="$colNam"/></xsl:attribute>
												<xsl:attribute name="java-field"/>
											</xsl:element>
										</xsl:if>
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
