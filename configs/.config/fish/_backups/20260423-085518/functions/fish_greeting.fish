function fish_greeting --description 'Show a time-based startup greeting'
    set -l hour (date +%H)

    set -l morning_greetings \
        'Namaste, bhai! Chal, aaj kuch solid code karte hain. ☀️' \
        'Greetings, fellow unit! Ready to convert caffeine into code? ☕' \
        'Good morning! Ready to debug the universe (or just our app) today? 🌌' \
        'Suprabhat, dost! Let\'s make today productive! 💻' \
        'Rise and shine! Ready to compile greatness? 🌅' \
        'Morning! Let\'s turn that coffee into commits. ☕→💻' \
        'Arre! Subah subah coding karne ka maza hi alag hai! 🚀' \
        'Hello World! Fresh start, fresh code. Let\'s do this! 🌍' \
        'Good morning! Time to make the magic happen. ✨'

    set -l afternoon_greetings \
        'Arre, mere dost! Code karne ke liye taiyaar ho? 🚀' \
        'Kya haal hai, dost? Chalo, bug-fixing shuru karein! 🐛' \
        'SYN! Ready to ACK our way through some logic? 🧠' \
        'Hey! Ready to script a future where everything compiles on the first try? 🖖🏽' \
        'Handshake initiated. 👋 Ready to make the magic happen?' \
        'What\'s kickin\', chicken? Ready to squash some bugs? 🐔' \
        'Afternoon, warrior! Let\'s ship some features. ⚓' \
        'Ready to ship it? 🛶 No looking back until the PR is merged!' \
        'Holla! 👋 Let\'s make this script look absolutely on fleek today.' \
        'Greetings! Ready to do some adulting today? Let\'s crush these commits. ☕'

    set -l evening_greetings \
        'Oye! Taiyaar ho world badalne ke liye? 💻🌙' \
        'Salutations! Shall we initiate a session of bug-free productivity? 👾' \
        'Yo! Ready to overclock our brains and ship some features? ⚓' \
        '01001000 01101001! Ready to push some commits? ⋈' \
        'Ahoy, matey! Ready to navigate the sea of syntax? 🦜' \
        'Let\'s compile 2026—one line at a time. 🔮 You in?' \
        'Ready to turn that software into hardware? Let\'s get to it! 🔩' \
        'Wassup, dawg? Ready to ship some code that\'s totally da bomb? 💣' \
        'Yo! Ready to get crunk on some logic? It\'s gonna be sick! 🤘' \
        'Cool beans! 🆒 Time to sit down and write some awesomesauce code.' \
        'Late night grind! The best code happens after dark. 🌃' \
        'Evening vibes activated. Let\'s make some nocturnal magic. 蝙'

    set -l greetings
    if test $hour -ge 5 -a $hour -lt 12
        set greetings $morning_greetings
    else if test $hour -ge 12 -a $hour -lt 18
        set greetings $afternoon_greetings
    else
        set greetings $evening_greetings
    end

    set -l random_index (random 1 (count $greetings))
    printf '\n  %s\n\n' $greetings[$random_index]
end
