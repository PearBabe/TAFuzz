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

#include <sstream>
#include <string>
#include <map>
#include <iostream>
#include <sys/time.h>

#ifndef ROMEO_WIN
#include <sys/resource.h>
#else
#include <windows.h>
#endif

using namespace std;

#include <logger.hh>

using namespace romeo;

#ifdef ROMEO_MAC
#include <mach/mach.h>
#include <mach/task.h>
int getmem (unsigned int *rss, unsigned int *vs)
{
    struct task_basic_info t_info;
    mach_msg_type_number_t t_info_count = TASK_BASIC_INFO_COUNT;

    if (KERN_SUCCESS != task_info(mach_task_self(), TASK_BASIC_INFO, (task_info_t)&t_info, &t_info_count))
    {
        return -1;
    }
    *rss = t_info.resident_size;
    *vs  = t_info.virtual_size;
    return 0;
}
#endif

void Logger::start(const string& s)
{
#ifdef ROMEO_PROFILE
    _start(s);
#endif 
}

void Logger::stop(const string& s)
{
#ifdef ROMEO_PROFILE
    _stop(s);
#endif 
}

void Logger::count(const string& s)
{
#ifdef ROMEO_PROFILE
    _count(s);
#endif 
}

void Logger::_start(const string& s)
{
    if (log.find(s) == log.end())
    {
        log[s].user_time = 0.0;
        log[s].sys_time = 0.0;
        log[s].span = true;
        log[s].nb = 0;
        log[s].memory = 0;
    }
    log[s].nb++;

#ifndef ROMEO_WIN
    struct rusage res;
    getrusage(RUSAGE_SELF, &res);
    log[s].user_time -= (double) res.ru_utime.tv_sec + (double) res.ru_utime.tv_usec / 1000000.0;
    log[s].sys_time -= (double) res.ru_stime.tv_sec + (double) res.ru_stime.tv_usec / 1000000.0;
#ifdef ROMEO_LINUX
    log[s].memory -= res.ru_maxrss;
#elif defined ROMEO_MAC
    unsigned int rss;
    unsigned int vs;
    getmem(&rss, &vs);
    log[s].memory -= rss; 
#endif
#else
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    log[s].user_time -= (double) t.QuadPart;
#endif
}

void Logger::_stop(const string& s)
{
#ifndef ROMEO_WIN
    struct rusage res;
    getrusage(RUSAGE_SELF, &res);
    log[s].user_time += (double) res.ru_utime.tv_sec + (double) res.ru_utime.tv_usec / 1000000.0;
    log[s].sys_time += (double) res.ru_stime.tv_sec + (double) res.ru_stime.tv_usec / 1000000.0;
#ifdef ROMEO_LINUX
    log[s].memory += res.ru_maxrss;
#elif defined ROMEO_MAC
    unsigned int rss;
    unsigned int vs;
    getmem(&rss, &vs);
    log[s].memory += rss; 
#endif
#else
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    log[s].user_time += (double) t.QuadPart;
#endif
}

void Logger::_count(const string& s)
{
    if (log.find(s) == log.end())
    {
        log[s].span = false;
        log[s].nb = 0;
    }
    log[s].nb++;

#ifndef ROMEO_WIN
    struct rusage res;
    getrusage(RUSAGE_SELF, &res);
    log[s].user_time -= (double) res.ru_utime.tv_sec + (double) res.ru_utime.tv_usec / 1000000.0;
    log[s].sys_time -= (double) res.ru_stime.tv_sec + (double) res.ru_stime.tv_usec / 1000000.0;
#ifdef ROMEO_LINUX
    log[s].memory -= res.ru_maxrss;
#elif defined ROMEO_MAC
    unsigned int rss;
    unsigned int vs;
    getmem(&rss, &vs);
    log[s].memory -= rss; 
#endif
#else
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    log[s].user_time -= (double) t.QuadPart;
#endif
}

void Logger::clear()
{
    log.clear();
}

void Logger::print()
{
    map<string,LogItem>::iterator i;
    for (i=log.begin(); i!=log.end(); i++)
    {
        string s = i->first;
        cout << s << ": "<< log[s].nb << "x ";
        if (log[s].span)
        {
            cout << times(s);
        }
        cout << endl;
    }
}

string Logger::times(const string& s)
{
    stringstream out;

    out.setf(ios::fixed, ios::floatfield);
    out.precision(1);
    
    const double tu = log[s].user_time;
    const double ts = log[s].sys_time;
    
#ifndef ROMEO_WIN
    out << "Time: "<< tu+ts << "s (total) = " << tu << "s (user) + " << ts << "s (system)";
#else
    LARGE_INTEGER freq;
    QueryPerformanceFrequency(&freq);
    out << "Time: "<< tu / ((double) freq.QuadPart)  << "s (total)";
#endif

    return out.str();
}

string Logger::memory(const string& s)
{
    stringstream out;

    out.setf(ios::fixed, ios::floatfield);
    out.precision(1);

    unsigned m = log[s].memory;
#ifdef ROMEO_LINUX
    out << "Max memory used: "<< (double) m / 1000.0 << "Mo"; 
#elif defined ROMEO_MAC
    out << "Max memory used: "<< (double) m / 1000000.0 << "Mo"; 
#endif

    return out.str();
}

