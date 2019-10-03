<?xml version="1.0" encoding="UTF-8"?>
<!--genere un fichier xml correspondant aux infos de persistance pour un module EJB donné-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
	<xsl:variable name="sModuleDir" select="document('module-dir.xml')/module-dir/@path"/>
	<xsl:template match="/">
		<xsl:variable name="EjbJarFileRef" select="*[local-name() = 'EjbRdbDocumentRoot']/*[local-name() = 'inputs'][@*[local-name() = 'type'] = 'ejb:EJBJar']/@href"/>
		<xsl:variable name="EjbJarFileId" select="substring-after($EjbJarFileRef, '#')"/>
		<xsl:element name="ejb-module-infos">
			<xsl:element name="module-pers-infos">
				<xsl:for-each select="*[local-name() = 'EjbRdbDocumentRoot']/*[local-name() = 'nested'][@*[local-name() = 'type'] = 'ejbrdbmapping:RDBEjbMapper']">
					<xsl:element name="entity">
						<xsl:element name="entity-name">
							<xsl:variable name="beanRef" select="*[local-name() = 'inputs'][@*[local-name() = 'type']]/@*[local-name() = 'href']"/>
							<xsl:variable name="beanId" select="substring-after($beanRef, '#')"/>
							<xsl:variable name="RelEjbJarFile" select="substring-before($beanRef, '#')"/>
							<xsl:value-of select="document(concat(string($sModuleDir), '/', string($RelEjbJarFile) ))/*[local-name() = 'ejb-jar'][@id = $EjbJarFileId]/*[local-name() = 'enterprise-beans']/*[local-name() = 'entity'][@id = $beanId]/ejb-name"/>
						</xsl:element>
						<xsl:element name="tables">
							<xsl:for-each select="*[local-name() = 'outputs'][@*[local-name() = 'type'] = 'RDBSchema:RDBTable']">
								<xsl:element name="table">
									<xsl:variable name="TableRef" select="@href"/>
									<xsl:variable name="TableId" select="substring-after($TableRef, '#')"/>
									<xsl:variable name="RelFilePath" select="substring-before($TableRef, '#')"/>
									<xsl:element name="table-name">
										<xsl:value-of select="document(concat(string($sModuleDir), '/', string($RelFilePath) ))/descendant::*[local-name() = 'RDBTable'][@*[local-name() = 'id'] = $TableId]/@name"/>
									</xsl:element>
									<xsl:for-each select="../*[local-name() = 'nested'][child::outputs[@*[local-name() = 'type'] = 'RDBSchema:RDBColumn']]">
										<xsl:for-each select="*[local-name() = 'outputs'][@*[local-name() = 'type'] = 'RDBSchema:RDBColumn']">
											<xsl:element name="column">
												<xsl:attribute name="name">
													<xsl:variable name="ColRef" select="@href"/>
													<xsl:variable name="ColId" select="substring-after($ColRef, '#')"/>
													<xsl:variable name="ColRelPath" select="substring-before($ColRef, '#')"/>
													<xsl:value-of select="document(concat(string($sModuleDir), '/', string($ColRelPath) ))/descendant::*[local-name() = 'RDBTable'][@*[local-name() = 'id'] = $TableId]/*[local-name() = 'columns'][@*[local-name() = 'id'] = $ColId]/@name"/>
												</xsl:attribute>
											</xsl:element>
										</xsl:for-each>

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
