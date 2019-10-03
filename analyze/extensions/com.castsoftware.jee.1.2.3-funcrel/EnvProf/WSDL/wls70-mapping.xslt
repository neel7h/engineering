<?xml version="1.0" encoding="ISO-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
	<xsl:output method="xml" version="1.0" encoding="ISO-8859-1" indent="yes"/>
	<xsl:template match="/web-services">
		<xsl:element name="webservices-impl">
		<xsl:if test="count(*[local-name() = 'web-service']) &gt; 0">
			<xsl:for-each select="*[local-name() = 'web-service']">
				<xsl:element name="serviceImpl">
					<xsl:attribute name="name"/>
					<xsl:element name="portTypeImpl">
						<xsl:attribute name="name"><xsl:value-of select="@portTypeName"/></xsl:attribute>
						<xsl:variable name="class_id" select="*[local-name() = 'components']/*[local-name() = 'java-class']/@name"/>
						<xsl:attribute name="implClassFQName"><xsl:value-of select="*[local-name() = 'components']/*[local-name() = 'java-class']/@class-name"/></xsl:attribute>
						<xsl:element name="cwClassId">5040</xsl:element>
						<xsl:if test="count(*[local-name() = 'operations']/*[local-name() = 'operation']) &gt; 0">
						<xsl:for-each select="*[local-name() = 'operations']/*[local-name() = 'operation'][@component = $class_id]">
							<xsl:element name="operationImpl">
								<xsl:attribute name="name"><xsl:value-of select="@method"/></xsl:attribute>
								<xsl:attribute name="implProcName"><xsl:value-of select="@method"/></xsl:attribute>
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
