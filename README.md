# Reporting utilities for SwimTopia / Meet Maestro 
This is a suite of custom reporting utilities for swim teams that use SwimTopia and Meet Maestro.  Our team is the Armada, so I called it our Treasure Chest.

It was developed with a lot of help from ChatGPT so there could be ample opportunity to optimize the code.  I am not a developer by trade so the important thing is that it works.  Feel free to use any or all of this code and adapt it for your own swim team.

## Combo Generator

As we know, Meet Maestro has no built-in concept of combining events.  This code accepts a Meet Maestro session report PDF, a number of pool lanes, and the desired combo strategy, and then parses the PDF and lets you know which events can be combined.  The list is available as both a PDF and CSV download.  The parameters are as follows:

* Only combine a girls/womens event with a boys/mens event in the same age group.
  * Example: 11-12 Girls 50yd Freestyle can be combined with 11-12 Boys 50yd Freestyle
* Remainder of girls/womens entries (entries % number of pool lanes) + remainder of boys/mens entries <= number of pool lanes
* Remainder >= 1 for both events (can't combine with an empty heat)
* The combo strategy sets how aggressive to be when combining events.  Some teams prefer an aggressive strategy while others don't.
  * Aggressive: remainder >= 1 for both events.  Produces the most combos.
  * Neutral: remainder >= 2 for both events.
  * Conservative: remainder >= 3 for both events.  Produces the fewest combos.

For parsing the PDF, between the various browsers and Microsoft's Windows 10/11 PDF printer I ran into three different types of PDF formatting that required different methods of parsing.  It tries each method in succession, with the last method being OCR.  The OCR method was added last and could probably be used for all PDFs since it simply converts each page to PNG.  It definitely works with PDFs saved from Chrome, Edge, and Firefox on Windows and Mac using those browsers' print -> "save as PDF" function, and with the Microsoft Print to PDF printer.

## Time Improvement Awards (Avery label format)

Meet Maestro has a built-in time improvement label report, but it compares against the swimmer's best _career_ time in an event.  This doesn't work if your team only bases awards on the best _season_ time.  Your team may also issue other awards that aren't supported by the Meet Maestro or SwimTopia reporting tools.  In our case these are the Triple Drop and Fast Fishy awards.

The time improvement award leverages the data in the SwimTopia Athlete Report Card.  Choose your options as necessary (possibly including unofficial meets if you have a practice meet/time trials to start the season), then run the report and download the CSV.  When the CSV is uploaded, the script combs through it, identifying meets that have times and letting you choose which meet to report on.  (This is nice since you don't need report cards from multiple points in time.)  Choose the reports you want and you are given options to download both the award labels (PDF formatted for an Avery 5160/8160/8460 template) and a PDF report of the output if needed for sanity checks.

Supported awards:

### Time Improvement

In order to qualify for a time improvement award in an individual event, the swimmer must already have a valid time (no DQs) in that event _in that season_.  Produces one label per improved time per swimmer.

### Triple Drop

Triple Drop is awarded to every swimmer that improves time in three individual events in the same meet.  Produces one label per swimmer.

### Fast Fishy

The Fast Fishy is the swimmer in each age/gender group with the highest cumulative time improvement.  This is NOT a net calculation and only factors in time improvements; for example, if a swimmer improves 3 seconds in one event and 4 seconds in another event, but adds 2 seconds in their third event, this is counted as a -7, not a -5.  Additionally, if a swimmer is a repeat winner they are labeled as such, and the next eligible swimmer that isn't also a repeat winner gets the award as well.  Produces one label per swimmer.

# Why Python?

I originally wanted to do this in Node.js, but I started with the combo generator and had all manner of issues getting Node libraries to parse the session report.  Python had more obvious turnkey solutions, so here we are.

# Questions

Contact me at paradox183@gmail.com.

# Disclaimer

This project is offered without any warranty or support and you are free to use it at your own risk.  As I said above, much of the code is AI-generated and likely not 100% optimized.  I am releasing it under the GNU General Public License.
