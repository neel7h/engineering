"""
Linking to java main method
"""
import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link
import logging
from collections import defaultdict
import os


class CallToProgram:
    
    def __init__(self, program_name, call_object):

        self.program_name = program_name
        self.call_object = call_object


class Program:
    
    def __init__(self, program_name, program_object):

        self.program_name = program_name
        self.program_object = program_object


class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):

        logging.info('Linking calls to programs')

        # 1. loading
        calls = [CallToProgram(e.get_property('CAST_CallToProgram.programName'), e) for e in application.objects().has_type('CAST_CallToProgram').load_property('CAST_CallToProgram.programName')]

        if not calls:
            logging.info('No call to programs : nothing to do')
            return
        
        # load the programs
        programs = defaultdict(list)        
        
        for program in application.objects().has_type('CAST_Program'):
            programs[program.get_name().lower()].append(Program(program.get_name(), program))

        if not programs:
            logging.info('No programs : nothing to do')
            return
        
        for call in calls:
            
            called_program_name = call.program_name.lower()
            
            # first try by name
            logging.debug('searching ' + called_program_name)
            
            if called_program_name in programs:
                for program in programs[called_program_name]:
                    logging.debug('creating link between ' + str(call.call_object) + ' and ' + str(program.program_object))
                    create_link('callLink', call.call_object, program.program_object)                    
            else:
                # if not found, search by name without extension
                logging.debug('second chance')
                if '.' in called_program_name:
                    
                    root, _ = os.path.splitext(called_program_name)
                    possibles = []
                    bests = []
                    if root in programs:
                        logging.debug('searching ' + root)
                        for program in programs[root]:
                            possibles.append(program.program_object)
                            
                            if called_program_name in program.program_object.get_fullname().lower():
                                # best ones are those whose fullname contains the extension (for Perl)
                                bests.append(program.program_object)
                    
                    if bests:
                        
                        for best in bests:
                            create_link('callLink', call.call_object, best)   
                    
                    else:
                        
                        for possible in possibles:
                            create_link('callLink', call.call_object, possible)   
                        
                        



