#include <iostream>
#include <chrono>
#include <thread>
#include <sstream>

#include "date.h"

using namespace std::chrono;

struct Time
{
    /** Obtain the current time via different clocks. */
    Time():
        systemTime(system_clock::now()),
        steadyTime(steady_clock::now()),
        highResolutionTime(high_resolution_clock::now())
    {
    }
    
    const time_point<system_clock> systemTime;
    const time_point<steady_clock> steadyTime;
    const time_point<high_resolution_clock> highResolutionTime;
};

template<typename Value>
std::string signedStr(Value value)
{
    std::ostringstream s;
    if (value >= 0)
        s << "+";
    s << value;
    return s.str();
}

void logTimeDiff(const Time& startTime, const Time& time)
{
    using namespace date;
    
    const auto systemElapsedUs = duration_cast<microseconds>(
        time.systemTime - startTime.systemTime).count();

    const auto steadyElapsedUs = duration_cast<microseconds>(
        time.steadyTime - startTime.steadyTime).count();
        
    const auto highResolutionElapsedUs = duration_cast<microseconds>(
        time.highResolutionTime - startTime.highResolutionTime).count();
    
    const auto steadyDiffUs = systemElapsedUs - steadyElapsedUs;
    const auto highResolutionDiffUs = systemElapsedUs - highResolutionElapsedUs;
    
    std::cout << time.systemTime
        << " steady " << signedStr(steadyDiffUs) << " us"
        << ", high_resolution " << signedStr(highResolutionDiffUs) << " us"
        << "\n";
}

int main()
{
    std::cout << "Comparing different std::chrono clocks.\n";
    
    const Time startTime;
    
    for (;;)
    {
        std::this_thread::sleep_for(seconds(10));
        const Time time;
        logTimeDiff(startTime, time);
    }    
}