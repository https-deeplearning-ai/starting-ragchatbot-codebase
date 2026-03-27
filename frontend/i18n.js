// Internationalization (i18n) translations
const translations = {
    en: {
        // Header
        title: 'Course Materials Assistant',
        subtitle: 'Ask questions about courses, instructors, and content',

        // Sidebar
        newChat: '+ New Chat',
        courses: 'Courses',
        numberOfCourses: 'Number of courses:',
        tryAsking: 'Try asking:',
        outlineOfCourse: 'Outline of a course',
        courseAboutChatbot: 'Courses about Chatbot',
        courseExplainingRAG: 'Courses explaining RAG',
        detailsOfLesson: "Details of a course's lesson",

        // Chat
        placeholder: 'Ask about courses, lessons, or specific content...',
        sources: 'Sources',
        welcome: 'Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?',

        // Error messages
        queryFailed: 'Query failed',
        errorLoadingCourses: 'Failed to load courses',
        noCourses: 'No courses available',
        failedToLoadCourses: 'Failed to load courses',

        // Language selector
        language: 'Language',
        chinese: '中文',
        english: 'English'
    },
    zh: {
        // Header
        title: '课程材料助手',
        subtitle: '提问关于课程、讲师和内容的问题',

        // Sidebar
        newChat: '+ 新建对话',
        courses: '课程',
        numberOfCourses: '课程数量：',
        tryAsking: '尝试提问：',
        outlineOfCourse: '课程大纲',
        courseAboutChatbot: '关于聊天机器人的课程',
        courseExplainingRAG: '解释RAG的课程',
        detailsOfLesson: '课程课时详情',

        // Chat
        placeholder: '提问关于课程、课时或具体内容...',
        sources: '来源',
        welcome: '欢迎使用课程材料助手！我可以帮助您解答关于课程、课时和具体内容的问题。您想了解什么？',

        // Error messages
        queryFailed: '查询失败',
        errorLoadingCourses: '加载课程失败',
        noCourses: '没有可用的课程',
        failedToLoadCourses: '加载课程失败',

        // Language selector
        language: '语言',
        chinese: '中文',
        english: 'English'
    }
};

// Get translation for a key in the current language
function t(key, lang = getCurrentLanguage()) {
    return translations[lang]?.[key] || translations['en']?.[key] || key;
}

// Get current language from localStorage or default to 'en'
function getCurrentLanguage() {
    return localStorage.getItem('language') || 'en';
}

// Set language and save to localStorage
function setLanguage(lang) {
    if (lang === 'en' || lang === 'zh') {
        localStorage.setItem('language', lang);
        return true;
    }
    return false;
}
