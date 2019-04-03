**This project is in an alpha state**

Librelaws
---------
Laws are bits of text evolving over time in a collaborative fashion where changes are comited and signed off by certain parties or governments. Often times there are long discussions and alternative proposals leading up to the final vote. Sounds like a perfect fit for git, does it not? A government creates or changes a law by patching the existing corpus and signing off on the commit. Discussions and voting results can be stored in the commit messages along with mentions of alternative proposals. Any paragraph of any law could be attributed to one particular government and the discussion leading up to it would just be one `git blame` away!

Unfortunately, (German) laws are only published online in their current states. Historical changes are only available in a non-machine readable (e.g the Bundesgesetzblatt in Germany). Discussions, votes, and alternative proposals have to be scrapped from the parliaments homepage. Its a bit of a mess! This project nevertheless tries to recreate such a `git log` of German laws by continuously monitoring the current versions at [gesetzte-im-internet.de](http://www.gesetzte-im-internet.de) and by scrapping the internet [archive.org](https://www.archive.org), [offene-gesetze.de](https://offenegesetze.de/), and [bundestag.de](https://www.bundestag.de). Lastly, everything is augmented with historical data so that we know whom to `blame` for a certain section by name and party.

*The goal is to create and maintain such a git history completely automatically.*
