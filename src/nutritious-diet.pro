QT       += core gui network
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET   = nutritious-diet
TEMPLATE = app

CONFIG  += c++17
# MSVC 下源文件按 UTF-8 编译，避免中文字符串乱码
msvc: QMAKE_CXXFLAGS += /utf-8

DEFINES += QT_DEPRECATED_WARNINGS

SOURCES += \
    main.cpp \
    app/services/ApiClient.cpp \
    app/services/ChatService.cpp \
    app/services/ExerciseService.cpp \
    app/services/NutritionService.cpp \
    app/services/ProfileService.cpp \
    app/services/RecognitionService.cpp \
    app/services/RecordService.cpp \
    app/services/StatsService.cpp \
    app/ui/ChatPage.cpp \
    app/ui/ExercisePage.cpp \
    app/ui/LoginDialog.cpp \
    app/ui/MainWindow.cpp \
    app/ui/ProfileDialog.cpp \
    app/ui/RecognitionPage.cpp \
    app/ui/RecordsPage.cpp \
    app/ui/StatsPage.cpp \
    app/ui/WeightRecordDialog.cpp \
    app/widgets/BarChart.cpp \
    app/widgets/DonutChart.cpp \
    app/widgets/DropImageArea.cpp \
    app/widgets/FoodPickerDialog.cpp \
    app/widgets/LineChart.cpp \
    app/widgets/MetricCard.cpp

HEADERS += \
    app/config.h \
    app/models/FoodItem.h \
    app/models/MealRecord.h \
    app/models/RecognitionCandidate.h \
    app/models/WeightRecord.h \
    app/services/ApiClient.h \
    app/services/ChatService.h \
    app/services/ExerciseService.h \
    app/services/NutritionService.h \
    app/services/ProfileService.h \
    app/services/RecognitionService.h \
    app/services/RecordService.h \
    app/services/StatsService.h \
    app/ui/ChatPage.h \
    app/ui/ExercisePage.h \
    app/ui/LoginDialog.h \
    app/ui/MainWindow.h \
    app/ui/ProfileDialog.h \
    app/ui/RecognitionPage.h \
    app/ui/RecordsPage.h \
    app/ui/StatsPage.h \
    app/ui/WeightRecordDialog.h \
    app/widgets/BarChart.h \
    app/widgets/DonutChart.h \
    app/widgets/DropImageArea.h \
    app/widgets/FoodPickerDialog.h \
    app/widgets/LineChart.h \
    app/widgets/MetricCard.h

RESOURCES += \
    app/resources.qrc
