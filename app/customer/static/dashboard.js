// calendar JS

const months = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];

const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

let dateObj = new Date(),
    year = dateObj.getFullYear(),
    month = dateObj.getMonth(),
    date = dateObj.getDate(),
    day = dateObj.getDay();

const currentDay = day;
const currentDate = date;
const currentMonth = month;
const currentYear = year;
// initialize dashboard state
document.querySelector("#date-selected").innerHTML = `${days[day]} ${date} ${months[month]}`; // current date selected is today date

const renderCal = () => {
    document.querySelector(".month-year").innerHTML = `${months[month]} ${currentYear}`;

    // render days
    let lastDatePrevMonth = new Date(year, month, 0).getDate(), // get last date of previous month
        firstDayCurrentMonth = new Date(year, month, 1).getDay(), // get first day of current month -> e.g. sunday = 0 / wednesday = 3
        lastDateCurrentMonth = new Date(year, month + 1, 0).getDate(), // get last date of current month
        lastDayCurrentMonth = new Date(year, month, lastDateCurrentMonth).getDay(); // get last day of current month -> e.g. monday = 0 / saturday = 5
        
    let datesTag = "";
    let monthNum = month + 1 // e.g. Jan: (month, or month index) 0 ; (monthNum) 1
    let dayCounter = 0;

    // dates from previous month
    let datePreviousMonth = "";
    for (let d = firstDayCurrentMonth; d > 0; d--) {
        datePreviousMonth = lastDatePrevMonth - d + 1;
        datesTag += `<li class="inactive dateToParse" id="${days[dayCounter % 7]}-${datePreviousMonth}-${monthNum-1}-${year}">${datePreviousMonth}</li>`;
        dayCounter++;
    }

    for (let i = 1; i <= lastDateCurrentMonth; i++) {
        // active month
        if (i == date && `${months[currentMonth]} ${currentYear}` == document.querySelector(".month-year").innerHTML) { 
            datesTag += `<li class="active dateToParse" id="${days[dayCounter % 7]}-${i}-${monthNum}-${year}">${i}</li>`;
            dayCounter++;
            continue;
        }
        datesTag += `<li class="dateToParse" id="${days[dayCounter % 7]}-${i}-${monthNum}-${year}">${i}</li>`;
        dayCounter++;
    }

    // dates from next month
    let dateNextMonth = "";
    for (let d = lastDayCurrentMonth; d <= 5; d++) {
        dateNextMonth = d - lastDayCurrentMonth + 1;
        datesTag += `<li class="inactive dateToParse" id="${days[dayCounter % 7]}-${dateNextMonth}-${monthNum+1}-${year}">${dateNextMonth}</li>`;
        dayCounter++;
    }

    document.querySelector(".date-number").innerHTML = datesTag;
    
}
renderCal();


// chevron JS
const chevron = document.querySelector(".bx-chevron");

// alternate month
chevron.addEventListener("click", () => {
    let chevronClassElements = chevron.className.split(" ");

    if (chevronClassElements[2] == "bx-chevron-right") { // chevron icon is 3rd class element
        chevronClassElements[2] = "bx-chevron-left";
        month += 1;
    }
    else {
        chevronClassElements[2] = "bx-chevron-right";
        month -= 1;
    }

    chevron.className = chevronClassElements.join(" ");

    // update calendar
    // if alternating between different years, update month and year
    if (month < 0 || month > 11) {
        dateObj = new Date();
        year = date.getFullYear();
        month = date.getMonth();
    }
    else { dateObj = new Date(); }

    renderCal();
    updateSessDisplay();
})

const icons = {
    "Swimming Pool": "bx-swim",
    "Fitness Room": "bx-dumbbell",
    "Squash Courts": "bx-baseball",
    "Sports Hall": "bxs-institution",
    "Climbing Wall": "bx-body",
    "Studio": "bx-street-view"
};

const badgeColors = {
    "general": ["bg-success", "text-white"],
    "class": ["bg-warning", "text-body-secondary"],
    "team": ["bg-danger", "text-white"],
    "all": ["bg-primary", "text-white"]
}

let selected_date;

// pre-process sessions display to show today's activities

let dateButtonDay = days[currentDay],
    dateButtonDate = currentDate,
    dateButtonMonth = currentMonth+1, // month number = month index + 1
    dateButtonYear = currentYear,
    type = "general";



// update sessions display 
const updateSessDisplay = () => {
    // get list of date buttons
    let dateButtons = document.querySelectorAll(".dateToParse");

    const updateDateDisplay = () => {
        dateButtons.forEach( button => {
            button.addEventListener("click", () => {
                dateButtonDay = button.id.split("-")[0],
                dateButtonDate = button.id.split("-")[1],
                dateButtonMonth = button.id.split("-")[2], 
                dateButtonYear = button.id.split("-")[3];
                $(selected_date).removeClass("current");
                $(button).addClass("current");
                selected_date = button;

                
                // update session display header 
                document.querySelector("#date-selected").innerHTML = `${dateButtonDay} ${dateButtonDate} ${months[dateButtonMonth-1]}`;

                generateHTTPRequest();
            })
        })
    }
    updateDateDisplay();

    let typeButtons = document.querySelectorAll(".typeToParse");
    const updateType = () => {
        typeButtons.forEach( button => {
            button.addEventListener("click", () => {
                // update type var then re-update date display
                type = button.id;
                generateHTTPRequest(); 
            })
        })
    }
    updateType();
}
updateSessDisplay();

const generateHTTPRequest = () => {
    var sessionContainer = $(".session-container") // find the element with session-container class
    var dataToParse = `${dateButtonYear}-${dateButtonMonth}-${dateButtonDate}-${type}` // FORMAT: YYYY-MM-DD-type

    $.ajax({
        url: '/customer/get_sessions/' + `${dataToParse}`,
        type: 'GET',
        contentType: "application/json; charset=utf-8",
        dataType: "json",

        success: function (response) {

            var listGroup = document.createElement("div");
            listGroup.classList.add("list-group", "mb-4");

            console.log(response);
            
            // For each of these 
            response.forEach(element => {
                
                // If there are any sessions 
                if (element.sessions.length) {
                    // Create list group item 
                    var listGroupItem = document.createElement("div");
                    listGroupItem.classList.add("list-group-item", "d-sm-flex", "p-3", "border", "border-solid");


                    // Create outer flex container
                    var flexOuter = document.createElement("div")
                    flexOuter.classList.add("d-flex", "gap-5", "w-100");


                    // Create icon
                    var icon = document.createElement("i");
                    var iconTag = icons[element.facility];
                    icon.classList.add("bx", iconTag, "bx-lg", "d-flex", "m-auto", "py-2");

                    // Create an inline container
                    var inlineDiv = document.createElement("div")
                    inlineDiv.classList.add("d-inline", "w-100");


                    // Header divider containing times and sessions badge
                    var headerDiv = document.createElement("div");


                    // Time header
                    var times = document.createElement("h5");
                    times.classList.add("d-flex", "justify-content-between", "mb-3", "text-secondary");

                    // Session number badge
                    var sessionsBadge = document.createElement("span");
                    var sessBadgeBGColor = badgeColors[type][0];
                    var sessBadgeTextColor = badgeColors[type][1];
                    sessionsBadge.classList.add("badge", sessBadgeBGColor, sessBadgeTextColor, "rounded-pill");
                    $(sessionsBadge).html(element.sessions.length); // number of sessions

                    // Time header inner html
                    // Append badge to time header
                    $(times).html(element.start_time + " to " + element.end_time);
                    $(times).append(sessionsBadge);

                    // Append time header to header divider
                    $(headerDiv).html(times);


                    // Facility + Activity container
                    var mainInfoContainer = document.createElement("div");

                    var facility = document.createElement("h5");
                    facility.classList.add("m-0");
                    $(facility).html(element.facility);

                    var activity = document.createElement("p");
                    activity.classList.add("m-0", "text-secondary");
                    $(activity).html(element.activity);

                    $(mainInfoContainer).html(facility);
                    $(mainInfoContainer).append(activity);


                    // Append header divider and facility + activity to inline container
                    $(inlineDiv).html(headerDiv);
                    $(inlineDiv).append(mainInfoContainer);


                    // Append icon and inline container to outer flex
                    $(flexOuter).html(icon);
                    $(flexOuter).append(inlineDiv);


                    // Append to list group item
                    $(listGroupItem).html(flexOuter);

                    // Append to list group
                    $(listGroup).append(listGroupItem);
                }
                
            });
            $(sessionContainer).html(listGroup);

        },
        // The function which will be triggered if any error occurs.
        error: function (error) {
            console.log(error);
        }
    });
}
generateHTTPRequest();