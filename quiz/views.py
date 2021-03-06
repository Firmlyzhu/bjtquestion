#-*- coding:utf-8 -*-
from django.shortcuts import render,redirect
from weibo import APIClient
from users.LoginRequired import *
from users.models import *
from django.http import HttpResponse
from Http.RequestMethods import *
from Http.JsonResponse import *
from quiz.models import *
import random,time
from datetime import datetime,timedelta

# Create your views here.
@RequestMethods("GET")
def index(request):
    return render(request,'index.html')

@LoginRequired
@RequestMethods("GET")
def main(request):
    user = request.user
    return render(request, 'main.html', {'user':user})

@RequestMethods("GET")
def finished(request):
    user = request.user
    return render(request, 'finished.html')

q1_num = 15
q2_num = 5
q3_num = 10
limit_time = 10
quiz_again_days = 1

def addquestions(status, level, num):
    questions = Question.objects.filter(level=level).all()
    random.seed(time.time())
    indexes = random.sample(range(len(questions)), num)
    for i in indexes:
        status.questions.add(questions[i])

def getoptions(question,quizstatus):
    random.seed(time.time())
    indexs = random.sample(range(4), 4)
    options = {}
    in2an = ['A', 'B', 'C', 'D']
    i = 0
    for index in indexs:
        if index == 0:
            options[in2an[i]] = question.optionA
        elif index == 1:
            options[in2an[i]] = question.optionB
        elif index == 2:
            options[in2an[i]] = question.optionC
        elif index == 3:
            options[in2an[i]] = question.optionD
        if question.answer == in2an[index]:
            quizstatus.answer = in2an[i]
            quizstatus.save()
        i += 1
    return options

def update_best(user, history):
    is_update = False
    if hasattr(user, 'besthistory'):
        besthistory = user.besthistory
        if besthistory.rightnum < history.rightnum or (besthistory.rightnum == history.rightnum and besthistory.use_time > history.use_time):
            besthistory.qnum = history.qnum
            besthistory.rightnum = history.rightnum
            besthistory.use_time = history.use_time
            besthistory.end_time = history.end_time
            besthistory.save()
            is_update = True
    else:
        best = BestHistory(user=user)
        best.qnum = history.qnum
        best.rightnum = history.rightnum
        best.use_time = history.use_time
        best.end_time = history.end_time
        best.save()
        is_update = True
    bests = BestHistory.objects.order_by('-rightnum','use_time')
    rank = 1
    for best in bests:
        if best.user == user:
            break
        rank += 1
    return [is_update, rank]

@LoginRequired
@RequestMethods("GET")
def endquiz(request):
   global q1_num, q2_num, q3_num
   total = q1_num + q2_num + q3_num
   quizstatus = request.user.quizstatus
   if quizstatus.now_qnum == 0:
       return redirect("/main/")
   else:
       history = QuizHistory(user=request.user, qnum=quizstatus.now_qnum, rightnum=quizstatus.now_rightnum)
       history.use_time = quizstatus.use_time
       history.save()
       quizstatus.now_qnum = 0
       quizstatus.delete()
       status = QuizStatus(user=request.user, now_qnum=0, now_rightnum=0, is_finished=True)
       status.qtime = datetime.now()
       status.save()
       #print(history.use_time)
       mins = int(history.use_time/60000)
       secs = float(history.use_time%60000/1000.0)
       [is_update, rank] = update_best(request.user, history)
       return render(request, 'finished.html', {'result':history, 'mins':mins, 'secs':secs, 'is_update':is_update, 'rank':rank})

@LoginRequired
@RequestMethods("GET")
def quiz(request):
   global q1_num, q2_num, q3_num
   total = q1_num + q2_num + q3_num
   quizstatus = request.user.quizstatus
   if (not quizstatus.now_qnum == 0) and (datetime.now() - quizstatus.qtime).total_seconds() > 60:
       return redirect("/endquiz/")
   if quizstatus.now_qnum == 0 and (datetime.now() - quizstatus.qtime).days < quiz_again_days:
       next_time = quizstatus.qtime+timedelta(days=quiz_again_days)
       time_str = next_time.strftime('%Y年%m月%d日%H时%M分')
       return HttpResponse("<script languagae='javascript'>alert('你已在%d天内参加过测试，请在%s以后再尝试答题');window.history.back(-1);</script>"%(quiz_again_days,time_str))
   if quizstatus.now_qnum == 0:
       addquestions(quizstatus, 1, q1_num)
       addquestions(quizstatus, 2, q2_num)
       addquestions(quizstatus, 3, q3_num)
       quizstatus.save()
   if quizstatus.is_finished == True:
       if quizstatus.now_qnum < total:
           quizstatus.now_qi = random.randint(0,29-quizstatus.now_qnum)
           quizquestions = quizstatus.questions.all()
           if len(quizquestions) < 30-quizstatus.now_qnum:
               diffnum = 30-quizstatus.now_qnum - len(quizquestions)
               questions = Question.objects.all()
               random.seed(time.time())
               indexes = random.sample(range(len(questions)), diffnum)
               for i in indexes:
                   quizstatus.questions.add(questions[i])
           now_question = quizstatus.questions.all()[quizstatus.now_qi]
           quizstatus.now_qnum += 1
           quizstatus.qtime = datetime.now()
           quizstatus.is_finished = False
           quizstatus.save()
           options = getoptions(now_question, quizstatus)
       else:
           return redirect("/endquiz/")
   else:
       now_question = quizstatus.questions.all()[quizstatus.now_qi]
       options = getoptions(now_question, quizstatus)
   t = quizstatus.qtime.timetuple()
   timestamp = int(time.mktime(t))*1000
   return render(request, 'quiz.html', {'user':request.user, 'question':now_question.question, 'options':options, 'now_qnum':quizstatus.now_qnum, 'total':total, 'qtime':timestamp})

@LoginRequired
@RequestMethods("POST")
def submit(request):
    option = request.POST.get('option',None)
    if option is None:
        print("option is None")
        return redirect("/")
    quizstatus = request.user.quizstatus
    if quizstatus.is_finished:
        return JsonResponse(False, "你无法提交该题答案了。")
    else:
        quizstatus.is_finished = True
        question = quizstatus.questions.all()[quizstatus.now_qi]
        quizstatus.questions.remove(question)
        delta = datetime.now() - quizstatus.qtime
        dseconds = delta.total_seconds()
        if dseconds >= float(limit_time):
            dseconds = limit_time
        quizstatus.use_time += int(dseconds*1000)
        quizstatus.save()
        if delta.seconds >= limit_time or option == 'E':
            return JsonResponse(False, "回答超时，请回答下一题！")
        else:
            print(option)
            print(question.answer)
            if option == quizstatus.answer:
                question.total += 1
                question.right += 1
                quizstatus.now_rightnum += 1
                quizstatus.save()
                question.save()
                return JsonResponse(True, "回答正确！")
            else:
                question.total += 1
                question.save()
                return JsonResponse(False,"回答错误！")

@LoginRequired
@RequestMethods("GET")
def rankings(request):
    bests = BestHistory.objects.order_by('-rightnum','use_time')
    return render(request, 'rankings.html', {'user':request.user, 'histories':bests})

@LoginRequired
@AdminRequired
@RequestMethods("GET")
def readquestions(request):
    infile = open("questions.txt")
    lines = infile.readlines()
    i = 0
    level = 1
    lines[0] = lines[0][3:]
    while i < len(lines):
        info = lines[i].decode('utf-8')
        print(info)
        if info.encode('utf-8')[0:6] == '初级':
            print(level)
            level = 1
        elif info.encode('utf-8')[0:6] == '中级':
            level = 2
        elif info.encode('utf-8')[0:6] == '高级':
            level = 3
        else:
            if not info.strip() == "":
                questiontxt = info
                optionA = lines[i+1].decode('utf-8')[2:].strip()
                optionB = lines[i+2].decode('utf-8')[2:].strip()
                optionC = lines[i+3].decode('utf-8')[2:].strip()
                optionD = lines[i+4].decode('utf-8')[2:].strip()
                ans = lines[i+6].decode('utf-8')[0].strip()
                que = Question(question=questiontxt, optionA=optionA, optionB=optionB, optionC=optionC, optionD=optionD)
                que.answer = ans
                que.level = level
                que.total = 0
                que.right = 0
                que.save()
                print(questiontxt)
                print(optionA)
                print(optionB)
                print(optionC)
                print(optionD)
                print(ans)
                i += 6
        i += 1
    return redirect('/')

@LoginRequired
@AdminRequired
@RequestMethods('GET')
def admin_interface(request):
    return render(request, 'admin.html', {'user':request.user})

@LoginRequired
@AdminRequired
@RequestMethods('GET')
def history(request):
    histories =  QuizHistory.objects.order_by('-end_time').all()
    return render(request, 'history.html', {'user':request.user, 'histories':histories})

@LoginRequired
@AdminRequired
@RequestMethods('GET')
def questions(request):
    questions =  Question.objects.all()
    return render(request, 'questions.html', {'user':request.user, 'questions':questions})

@LoginRequired
@AdminRequired
@RequestMethods('GET')
def query_question(request):
    qid = request.GET.get('qid',None)
    if qid is None:
        return JsonResponse(False,"没有qid参数")
    res = {'qid':qid}
    questions = Question.objects.filter(id=qid)
    if not questions.exists():
        return JsonResponse(False,"没找到该问题")
    question = questions.get(id=qid)
    res['question'] = question.question
    res['optionA'] = question.optionA
    res['optionB'] = question.optionB
    res['optionC'] = question.optionC
    res['optionD'] = question.optionD
    res['answer'] = question.answer
    res['level'] = question.level
    return JsonResponse(True,"",res)

@LoginRequired
@AdminRequired
@RequestMethods('POST')
def modify_question(request):
    form = request.POST
    qid = form.get('questionid',None)
    if qid is None:
        return JsonResponse(False,"没有qid参数")
    questions = Question.objects.filter(id=qid)
    if not questions.exists():
        return JsonResponse(False,"没找到该问题")
    question = questions.get(id=qid)
    question.question = form['question']
    question.optionA = form['optionA']
    question.optionB = form['optionB']
    question.optionC = form['optionC']
    question.optionD = form['optionD']
    question.answer = form['answer']
    if form['level'].encode('utf-8') == '初级':
        question.level = 1
    elif form['level'].encode('utf-8') == '中级':
        question.level = 2
    else:
        question.level = 3
    question.save()
    return redirect("/admin_interface/questions/")

@LoginRequired
@AdminRequired
@RequestMethods('POST')
def delete_question(request):
    qid = request.POST.get('qid',None)
    if qid is None:
        return JsonResponse(False,"没有qid参数")
    res = {'qid':qid}
    questions = Question.objects.filter(id=qid)
    if not questions.exists():
        return JsonResponse(False,"没找到该问题")
    question = questions.get(id=qid)
    question.delete()
    return JsonResponse(True,"删除成功")

@LoginRequired
@AdminRequired
@RequestMethods('POST')
def add_question(request):
    form = request.POST
    question = Question()
    question.question = form['aquestion']
    question.optionA = form['aoptionA']
    question.optionB = form['aoptionB']
    question.optionC = form['aoptionC']
    question.optionD = form['aoptionD']
    question.answer = form['answer']
    if form['level'].encode('utf-8') == '初级':
        question.level = 1
    elif form['level'].encode('utf-8') == '中级':
        question.level = 2
    else:
        question.level = 3
    question.total = 0
    question.right = 0
    question.save()
    return redirect("/admin_interface/questions/")
