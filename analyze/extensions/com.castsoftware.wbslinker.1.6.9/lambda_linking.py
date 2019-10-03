"""
AWS lambda
Linking between Lambda Call to lambda receive
"""
import cast_upgrade_1_5_25 # @UnusedImport
import logging
from collections import defaultdict
from cast.application import ApplicationLevelExtension, create_link


class CallToLambda:
    
    def __init__(self, lambda_name, o=None):
        
        self.lambda_name = lambda_name
        self.object = o


class Lambda:
    
    def __init__(self, lambda_name, o=None):
        
        self.lambda_name = lambda_name
        self.object = o


def link(calls, lambdas):
    """
    Link and returns a list of pair CallToLambda, Lambda
    
    :param calls: list(CallToLambda)
    :param lambdas: defaultdict(list); name to list(Lambda)
    
    """
    result = []
    
    for call in calls:
        
        try:
            
            for _lambda in lambdas[call.lambda_name]:
                
                result.append((call, _lambda))
        
        except KeyError:
            pass
    
    
    return result


class ExtensionApplication(ApplicationLevelExtension):
    
    def end_application(self, application):

        logging.info('Linking lambdas')

        # 1. loading
        calls = [CallToLambda(e.get_name(), e) for e in application.objects().has_type('CAST_CallTo_AWS_Lambda')]

        if not calls:
            logging.info('No call to lambdas : nothing to do')
            return
        
        # load the programs
        lambdas = defaultdict(list)        
        
        for _lambda in application.objects().has_type('CAST_AWS_Lambda'):
            lambdas[_lambda.get_name()].append(Lambda(_lambda.get_name(), _lambda))

        if not lambdas:
            logging.info('No lambdas : nothing to do')
            return
    
        links = link(calls, lambdas)
        
        # create links
        for call, service in links:
            
            create_link('callLink', call.object, service.object)

    
    