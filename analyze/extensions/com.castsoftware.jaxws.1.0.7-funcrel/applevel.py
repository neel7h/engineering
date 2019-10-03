import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link # @UnresolvedImport
import logging


class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):
                    
        jvServiceObjList =  list(application.objects().has_type('SOAP_JV_SERVICE'))
                   
        for obj in application.objects().has_type('JV_METHOD').load_property('CAST_CalledWebService.wsname'):
            if obj.get_property('CAST_CalledWebService.wsname') is not None:
                
                wsname = obj.get_property('CAST_CalledWebService.wsname')
                allWsName = wsname.split(':')
                
                for wsObj in jvServiceObjList:
                    for wsn in allWsName:
                        if wsn != '' and wsn.casefold() == wsObj.get_name().casefold():
                            logging.info('------'+ wsn + '------' + wsObj.get_name().casefold())
                            create_link('callLink', obj, wsObj)
        
        