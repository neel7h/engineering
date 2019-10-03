<?xml version="1.0" encoding="UTF-8"?>

<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:variable name="sModuleDir" select="document('module-dir.xml')/module-dir/@path"/>
	<xsl:template match="/">
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
				<xsl:for-each select="weblogic-ejb-jar/weblogic-enterprise-bean[entity-descriptor]">
					<xsl:variable name="persId"      select="entity-descriptor/persistence/persistence-use/type-identifier"/>
					<xsl:variable name="persVers"    select="entity-descriptor/persistence/persistence-use/type-version"/>
					<xsl:variable name="persStorage" select="entity-descriptor/persistence/persistence-use/type-storage"/>
					<xsl:element name="entity">
						<xsl:variable name="ejbName" select="ejb-name"/>
						<xsl:element name="entity-name">
							<xsl:value-of select="$ejbName"/>
						</xsl:element>
						<xsl:element name="tables">
						
							<!-- We have a RDBMS EJB -->
							<xsl:if test="string($persId) = 'WebLogic_CMP_RDBMS'">
								<!-- <type-storage> points to weblogic-ejb-rdbms-jar.xml; read database info from it -->
								<xsl:for-each select="document(concat(string($sModuleDir), '/', string($persStorage) ))/weblogic-rdbms-jar/weblogic-rdbms-bean[ejb-name = $ejbName]/table-map">
									<xsl:element name="table">
										<xsl:element name="table-name">
											<xsl:value-of select="table-name"/>
										</xsl:element>
										<xsl:for-each select="field-map[cmp-field]">
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="dbms-column"/></xsl:attribute>
												<xsl:attribute name="java-field"><xsl:value-of select="cmp-field"/></xsl:attribute>
											</xsl:element>
										</xsl:for-each>
									</xsl:element>
								</xsl:for-each>
							</xsl:if>
							
							<!-- We have a Toplink EJB -->
							<xsl:if test="string($persId) = 'TopLink_CMP'">
								<!-- <type-storage> points to toplink-ejb-jar.xml file; open it and read the path to TopLink project.xml -->
								<xsl:variable name="persDoc" select="document(string($persStorage) )/toplink-ejb-jar/session/project-xml"/>
								
								<!-- Read database info from the TopLink project.xml -->
								<xsl:for-each select="document(concat(string($sModuleDir), '/', string($persDoc)) )/project/descriptors/descriptor/tables/table">
									<xsl:element name="table">
										<xsl:element name="table-name">
											<xsl:value-of select="."/>
										</xsl:element>
										<xsl:for-each select="field-map[cmp-field]">
											<xsl:element name="column">
												<xsl:attribute name="name"><xsl:value-of select="dbms-column"/></xsl:attribute>
												<xsl:attribute name="java-field"><xsl:value-of select="cmp-field"/></xsl:attribute>
											</xsl:element>
										</xsl:for-each>
									</xsl:element>
								</xsl:for-each>
							</xsl:if>
							
						</xsl:element>
					</xsl:element>
				</xsl:for-each>				
			</xsl:element>
		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
