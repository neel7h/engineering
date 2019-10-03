<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
	<xsl:output method="xml" version="1.0" encoding="ISO-8859-1" indent="yes" />
	<xsl:template match="/">
		<xsl:element name="webservices-impl">
		<xsl:if test="count(*[local-name() = 'definitions']/*[local-name() = 'service']) &gt; 0">
			<xsl:for-each select="*[local-name() = 'definitions']/*[local-name() = 'service']">
				<xsl:element name="serviceImpl">
					<xsl:attribute name="name"><xsl:value-of select="@name" /></xsl:attribute>
					<xsl:attribute name="wsdlFile"><xsl:value-of select="document('module-dir.xml')/module-dir/@wsdlFile" /></xsl:attribute>
					<xsl:if test="count(*[local-name() = 'port']) &gt; 0">
					<xsl:for-each select="*[local-name() = 'port']">
						<xsl:if test="contains(@binding, ':')">
							<xsl:variable name="bindingName" select="substring-after(@binding, ':')" />
							<xsl:element name="portTypeImpl">
								<xsl:attribute name="name"><xsl:value-of select="substring-after(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/@type, ':')" /></xsl:attribute>
								<xsl:attribute name="implClassFQName" />
								<xsl:if test="count(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']) &gt; 0">
								<xsl:for-each select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']">
									<xsl:element name="operationImpl">
										<xsl:attribute name="name"><xsl:value-of select="@name" /></xsl:attribute>
										<xsl:variable name="opName" select="*[local-name() = 'operation']/@soapAction" />
										<xsl:call-template name="Loop">
											<xsl:with-param name="opName1" select="$opName" />
										</xsl:call-template>
										<!--COM Method -->
										<xsl:element name="cwClassId">4340</xsl:element>
										<!-- VB Function -->
										<xsl:element name="cwClassId">4170</xsl:element>
										<!-- VB Sub -->
										<xsl:element name="cwClassId">4180</xsl:element>
									</xsl:element>
								</xsl:for-each>
								</xsl:if>

							</xsl:element>
						</xsl:if>
						<xsl:if test="not(contains(@binding, ':'))">
							<xsl:variable name="bindingName" select="@binding" />
							<xsl:element name="portTypeImpl">
								<xsl:attribute name="name"><xsl:value-of select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/@type" /></xsl:attribute>
								<xsl:attribute name="implClassFQName" />
								<xsl:if test="count(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']) &gt; 0">
								<xsl:for-each select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']">
									<xsl:element name="operationImpl">
										<xsl:attribute name="name"><xsl:value-of select="@name" /></xsl:attribute>
										<xsl:variable name="opName" select="*[local-name() = 'operation']/@soapAction" />
										<xsl:call-template name="Loop">
											<xsl:with-param name="opName1" select="$opName" />
										</xsl:call-template>
										<!--COM Method -->
										<xsl:element name="cwClassId">4340</xsl:element>
										<!-- VB Function -->
										<xsl:element name="cwClassId">4170</xsl:element>
										<!-- VB Sub -->
										<xsl:element name="cwClassId">4180</xsl:element>
									</xsl:element>
								</xsl:for-each>
								</xsl:if>

							</xsl:element>
						</xsl:if>
					</xsl:for-each>
					</xsl:if>

				</xsl:element>
			</xsl:for-each>
		</xsl:if>

		</xsl:element>
	</xsl:template>
	<xsl:template name="Loop">
		<xsl:param name="opName1" />
		<xsl:choose>
			<xsl:when test="contains($opName1, '/')">
				<xsl:call-template name="Loop">
					<xsl:with-param name="opName1" select="substring-after($opName1, '/')" />
				</xsl:call-template>
			</xsl:when>
			<xsl:otherwise>
					<xsl:attribute name="implProcName"><xsl:value-of select="$opName1" /></xsl:attribute>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>
</xsl:stylesheet>
