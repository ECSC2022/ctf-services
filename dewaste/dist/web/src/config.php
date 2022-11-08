<?php

define("BASEURL", getenv("BASEURL") ?: "http://localhost:8080");
define("PLANT_NAME", "DEWASTE");
define("REPORT_APP_URL", getenv("REPORT_APP_URL") ?: '#');

return [
    // Base url for the web application
    "baseUrl" => BASEURL,
    "plantName" => PLANT_NAME,

    "db" => [
        "host" => getenv("DB_HOST") ?: "localhost",
        "user" => getenv("DB_USER") ?: "root",
        "password" => getenv("DB_PASSWORD") ?: "",
        "name" => getenv("DB_NAME") ?: "chal",
    ],

    "digitalItems" => [
        // maximum file size of uploaded digital items
        "maxFileSize" => 1 * 1000 * 1000,
    ],

    "analysis" => [
        "file" => [
            "tmpfolder" => getenv("ANALYSIS_FILE_TMPFOLDER") ?: '/var/lib/recycling_plant',
        ],
    ],

    "report_app" => [
        "url" => REPORT_APP_URL,
    ],
];
