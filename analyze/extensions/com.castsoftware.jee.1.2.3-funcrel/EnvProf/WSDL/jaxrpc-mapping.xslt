<?xml version="1.0" encoding="ISO-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
	<xsl:output method="xml" version="1.0" encoding="ISO-8859-1" indent="yes"/>
	<xsl:variable name="moduleDir" select="document('module-dir.xml')/module-dir/@path"/>
	<xsl:variable name="webXmlFile" select="concat($moduleDir, '\', 'META-INF\webservices.xml')"/>
	<xsl:template match="/">
		<xsl:element name="webservices-impl">
		<xsl:if test="count(*[local-name() = 'java-wsdl-mapping']/*[local-name() = 'service-endpoint-interface-mapping']) &gt; 0">
			<xsl:for-each select="*[local-name() = 'java-wsdl-mapping']/*[local-name() = 'service-endpoint-interface-mapping']">
				<xsl:element name="serviceImpl">
					<xsl:variable name="inputSource" select="concat($moduleDir, '\',  translate(document($webXmlFile)/module-dir/@wsdlFile, '/', '\'))"/>
					<xsl:variable name="webXmlMappingFile" select="concat($moduleDir, '\',  translate(document($webXmlFile)/*[local-name() = 'webservices']/*[local-name() = 'webservice-description']/*[local-name() = 'jaxrpc-mapping-file'] , '/', '\'))"/>
					<xsl:if test="inputSource = webXmlMappingFile ">
						<xsl:attribute name="name">
							<xsl:value-of select=" document($webXmlFile)/*[local-name() = 'webservices']/*[local-name() = 'webservice-description']/*[local-name() = 'webservice-description-name']"/>
						</xsl:attribute>
						<!-- Recuperer de webservices.xml -->
						<xsl:attribute name="wsdlFile">
							<xsl:value-of select="concat($moduleDir, document($webXmlFile)/*[local-name() = 'webservices']/*[local-name() = 'webservice-description']/*[local-name() = 'wsdl-file'])"/>
						</xsl:attribute>
					</xsl:if>
					<xsl:element name="portTypeImpl">
						<xsl:if test="contains(*[local-name() = 'wsdl-port-type'], ':')">
							<xsl:attribute name="name"><xsl:value-of select="substring-after(*[local-name() = 'wsdl-port-type'], ':')"/></xsl:attribute>
						</xsl:if>
						<xsl:if test="contains(*[local-name() = 'wsdl-port-type'], ':') = false">
							<xsl:attribute name="name"><xsl:value-of select="*[local-name() = 'wsdl-port-type']"/></xsl:attribute>
						</xsl:if>
						<xsl:attribute name="implClassFQName"><xsl:value-of select="*[local-name() = 'service-endpoint-interface']"/></xsl:attribute>
						<!-- Java Interface -->
						<xsl:element name="cwClassId">5030</xsl:element>
						<xsl:if test="count(*[local-name() = 'service-endpoint-method-mapping']) &gt; 0">
						<xsl:for-each select="*[local-name() = 'service-endpoint-method-mapping']">
							<xsl:element name="operationImpl">
								<xsl:attribute name="name"><xsl:value-of select="*[local-name() = 'wsdl-operation']"/></xsl:attribute>
								<xsl:attribute name="implProcName"><xsl:value-of select="*[local-name() = 'java-method-name']"/></xsl:attribute>
								<!-- Java Method -->
								<xsl:element name="cwClassId">5070</xsl:element>
							</xsl:element>
						</xsl:for-each>
						</xsl:if>

					</xsl:element>
				</xsl:element>
			</xsl:for-each>
		</xsl:if>

		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
