/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to perform
parametric model checking on timed and hybrid systems.

This software is governed by the CeCILL license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

The fact that you are presently reading this means that you have had
knowledge of the CeCILL license and that you accept its terms. */

#include <iostream>
#include <fstream>
#include <string>
#include <cstdlib>
#include <ctime>
#include <map>

#include <function.hh>
#include <cts.hh>
#include <job.hh>
#include <parser_data.hh>

#include <color_output.hh>

#ifndef ROMEO_WIN
#include <signal.h>
#endif

int yyparse(void);
extern FILE * yyin;
extern int yydebug;

using namespace std;
using namespace romeo;

ParserData * pdata;

void ctrlc_handler(int no)
{
    Job::stop = true;
}

void start_error(char* name)
{
    string filename = name;
    const size_t last_slash = filename.find_last_of("\\/");
    if (string::npos != last_slash)
        filename.erase(0, last_slash + 1);
    
    cerr << info_tag(color_output) << filename << " by Didier Lime, École Centrale de Nantes" << endl;
    cerr << info_tag(color_output) << ROMEO_VERSION << endl;
    cerr << error_tag(color_output) << "Usage: " << filename << " [-q|-m|-v] filename" << endl;
    exit(1);
}

int main(int argc, char** argv)
{
#ifndef ROMEO_WIN
    struct sigaction act;
	act.sa_handler = &ctrlc_handler;
	act.sa_flags = 0;
	sigemptyset(&act.sa_mask);

	if (sigaction(SIGINT, &act, NULL) == -1) {
			perror("sigaction");
			return 1;
	}
#endif

    string filename;
    map<string,string> options;
    //bool interactive = false;
    
    if (argc < 2)
        start_error(argv[0]);

    // Initialize random seed
    srand(time(nullptr));
    
    // Command line
    for (int i=1; i<argc; i++)
    {
        const string arg = argv[i];
        if (arg == "-v")
        {
            options["verbose"] = "true";
        } else if (arg == "-q") {
            options["quiet"] = "true";
        } else if (arg == "-m") {
            color_output = false;
        //} else if (arg == "-i") {
        //    interactive = true;
        } else if (arg[0] == '-') {
            cout << warning_tag(color_output) << "Ignored unknown flag: " << arg << endl;
        } else {
            filename = arg;
        }
    }

    if (filename == "")
        start_error(argv[0]);

    yyin = fopen(filename.c_str(), "r");
    if (yyin == NULL)
    {
        cerr << error_tag(color_output) << "Cannot open file: " << flush << filename<< endl;
        exit(1);
    }

    // Parse it
    pdata= new ParserData();
         
    // yydebug = 1;
    if (yyparse()) { exit(1); };

    fclose(yyin);

    vector<Job*>::iterator i;
    for (i = pdata->jobs.begin(); i != pdata->jobs.end(); i++)
    {
        CTS::current_cts = &(*i)->cts;
        //cout << (*i)->cts << endl;
        (*i)->add_options(options);
        (*i)->start();
        delete *i;
    }


    delete pdata;


    return 0;
}

