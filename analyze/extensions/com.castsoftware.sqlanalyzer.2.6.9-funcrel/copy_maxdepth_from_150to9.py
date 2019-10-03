import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension # @UnresolvedImport
import logging
import traceback
import logger


class CopyMaxDepthToMaxSQLSubqueriesNestedLevels(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        copy maxDepth property from CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth (150, 32)
            to CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels (9, 1006) 
            which  is open for all technologies, because the 1st one is hard coded  for new sql analyzers
        """
        logging.debug("copy CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth to CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels")
        
        application.declare_property_ownership('CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels',['SQlScriptMetricable'])

        try: 
            for o in application.objects().has_type('SQlScriptMetricable').load_property('CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth'):
                valueOfMaxDepth = o.get_property('CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth')
                if valueOfMaxDepth:
                    o.save_property('CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels', valueOfMaxDepth)
        except:
            logger.warning('SQL-011', 'Internal issue during copy of CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth to CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels, because of %s ' % traceback.format_exc())             