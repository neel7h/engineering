import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension # @UnresolvedImport
import logging
import traceback
import logger


class CopyMaxDepthToNumberOfSubqueries(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        copy maxDepth property from CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth (150, 32)
            to CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries (9, 3) 
            when the MA V2 regexp cannot detect subqueries
        """
        logging.debug("copy CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth to CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries")
        
        application.declare_property_ownership('CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries',['SQlScriptMetricable'])

        try: 
            for o in application.objects().has_type('SQlScriptMetricable').load_property('CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth').load_property('CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries'):
                valueOfMaxDepth = o.get_property('CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth')
                valueofNumberOfSubqueries = o.get_property('CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries')
                if valueOfMaxDepth and not valueofNumberOfSubqueries:
                    o.save_property('CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries', valueOfMaxDepth)
                elif valueofNumberOfSubqueries:
                    # be careful, we should always set a value, so this is why this else is here
                    # because, by default all values are deleted
                    o.save_property('CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries', valueofNumberOfSubqueries)
        except:
            logger.warning('SQL-010', 'Internal issue during copy of CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth to CAST_MetricAssistant_Metric_numberOfSubqueries.numberOfSubqueries, because of %s ' % traceback.format_exc())                   