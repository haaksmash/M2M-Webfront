from django.db import models
from django.contrib.auth.models import User

RATING_CHOICES = (
					(1,'1'),
					(2,'2'),
					(3,'3'),
					(4,'4'),
					(5,'5'),
					(6,'6'),
					(7,'7'),
					(8,'8'),
					(9,'9'),
					(10,'10'),
				)

DAY_CHOICES = (
				('M', "Monday"),
				("T", "Tuesday"),
				("W", "Wednesday"),
				("R", "Thursday"),
				("F", "Friday"),
				("S", "Saturday"),
				("U", "Sunday")
			)

CAMPUS_CHOICES = (
					('SC', 'Scripps'),
					('PZ', 'Pitzer'),
					('PO', 'Pomona'),
					('CM', 'CMC'),
					('HM', 'Harvey Mudd'),
					('CG', 'CGU'),
				)

BUILDING_CHOICES = (
					('HMC',( 
						('BK', "Beckman"),
						("GA", "Galileo"),
						("HOSH", "Hoch"),
						('JA', "Jacobs"),
						("KE", "Keck"),
						("LAC", "LAC"),
						("ON", "Olin"),
						("PA", "Parsons"),
						("PL", "Platt"),
						("SP", "Sprague"),
						("TG", "TG"),
						)
					),
					('Pitzer',(
							('ATN', "Atherton Hall"),
							('AV', "Avery Hall"),
							("BD", "E&E Broad Center"),
							("BE", "Bernard Hall"),
							("FL", "Fletcher Hall"),
							("GC", "Gold Student Center"),
							("GR", "Grove House"),
							("HO", "Holden Hall"),
							("MC", "McConnell Center"),
							("MH", "Mead Hall"),
							("OT", "Pitzer in Ontario"),
							("SB", "Sanborn Hall"),
							("SC", "Scott Hall"),
							
							)
					),
					('Pomona', (
							('AN', 'Andrew Science Bldg'),
							('BRDG', "Bridges Auditorium"),
							('BT', "Brackett Observatory"),
							('CA', "Carnegie Building"),
							("CR", "Crookshank Hall"),
							("EDMS", "Edmunds Building"),
							("GIBS", "Gibson Hall"),
							("HN", "Social Science Bldg"),
							("ITB", "Information Tech Bldg"),
							("LB", "Bridges Hall"),
							("LE", "Le Bus Court"),
							("LINC", "Lincoln Building"),
							("MA", "Mason Hall"),
							("ML", "Millikan Lab"),
							("OLDB", "Oldenbourg Center"),
							("PD", "Pendleton Dance Center"),
							("PR", "Pearsons Hall"),
							("RA", "Rains Center"),
							("REM", "Rembrandt Hall"),
							("SA", "Seaver Computing Ctr"),
							("SCC", "Smith Campus Center"),
							("SCOM", "Seaver Commons"),
							("SE", "Seaver South Lab"),
							("SL", "Seeley Science Library"),
							("SN", "Seaver North Lab"),
							("SVBI", "Seaver Bio Bldg"),
							("TE", "Seaver Theatre"),
							("THAT", "Thatcher Music Bldg"),
							("TR", "Biology Trailers"),
							)
					),
					('Scripps', (
							('AT', "Athletic Facility"),
							("BL", "Balch Hall"),
							("DN", "Richardson Studio"),
							("FRA", "Frankel Hall"),
							('HM', 'Edwards Humanities'),
							("LA", "Lang Art Studios"),
							("MT", "Malott Commons"),
							("PAC", "Performing Arts Center"),
							("ST", "Steele Hall"),
							("TIER", "Tiernant Field House"),
							("VN", "Vita Nova Hall"),
							)
					),					
					('CMC', (
							('AD', 'Adams Hall'),
							('BC', "Bauer South"),
							('BZ', 'Biszantz Tennis Center'),
							("DU", "Ducey Gym"),
							('RN', "Roberts North"),
							('RS', "Roberts South"),
							("SM", "Seaman Hall"),
							)
					),
					('CGU', (
							('BU', 'Burkle Building'),
							)
					),
					('CUC',(
						('HD', "Honnold/Mudd Library"),
						("KS", "Keck Science Center"),
						("SSC", "Student Services Center"),
						)
					),
				)

# Create your models here.
class Course(models.Model):
	''' a course in the 5C catalogue '''
	# e.g., 'Financial Economics', etc.
	title = models.CharField(max_length=50)
	# e.g., Computer Science, Mathematics, etc.
	department = models.ForeignKey('Department')
	semester = models.CharField(max_length=4, help_text="e.g., <em>FA12</em>")
	
	# the ECON in 'ECON104 HM' - should be able to get this from department,
	# but sometimes the code doesn't match the dept. Which is dumb.
	codeletters = models.CharField(max_length=50)
	# the 104 in 'ECON104 HM'
	codenumbers = models.IntegerField()
	# the HM in 'ECON104 HM'
	campus = models.CharField(max_length=2, default="HM", choices=CAMPUS_CHOICES)
	prerequisites = models.ForeignKey('self', blank=True)
	campus_restricted = models.BooleanField(default=False)
	
	mudd_creds = models.DecimalField(decimal_places=2, max_digits=3, default=3.00)

	description = models.TextField(blank=True, default="No description available for this course")

	def __unicode__(self):
		return u"{}{:03d} {}".format(self.codeletters, self.codenumbers, self.campus)

class CourseReview(models.Model):
	course = models.ForeignKey(Course)
	reviewer = models.ForeignKey(User)
	
	toughness = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="1 being the easiest")
	quality = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="1 being the worst")
	
	review = models.TextField()

	class Meta:
		unique_together = (('course','reviewer'))

	def __unicode__(self):
		return "Review of {} by {}".format(self.course, self.reviewer)

class Section(models.Model):
	course = models.ForeignKey(Course)
	professor = models.ForeignKey('Professor')
	number = models.IntegerField()
	
	seats = models.IntegerField()
	openseats = models.IntegerField()
	
	buildings = models.CharField(max_length=300, choices=BUILDING_CHOICES)
	room = models.CharField(max_length=30)
	
		
	times = models.ManyToManyField('TimeSlot', related_name="sections")
	
	@property
	def meet_times(self):
		return eval(self.meeting_times)
	
	class Meta:
		unique_together = (('course','number'))

	def __unicode__(self):
		return u"{} - {:02d}".format(self.course, self.number)

class Major(models.Model):
	''' a major at the 5C's (Specifically, HMC)'''
	
	# e.g., "Computer Science", "Math/Bio", etc.
	title = models.CharField(max_length=50)
	
	department = models.ForeignKey('Department')
	
	required_courses = models.ManyToManyField(Course, related_name='is_required_for')
	
	electives = models.ManyToManyField(Course, related_name='is_elective_for')
	
	credit_requirement = models.IntegerField()
	electives_required = models.IntegerField()
	
class Professor(models.Model):
	''' a Professor at the 5C's '''
	name = models.CharField(max_length=100)
	departments = models.ManyToManyField('Department')
	bio = models.TextField(blank=True, default="No bio available for this professor.")

	@property
	def toughness(self):
		reviews = self.professorreview_set.all()
		return float(sum([x.grading_toughness for x in reviews]))/len(reviews)

	@property
	def likeability(self):
		reviews = self.professorreview_set.all()
		return float(sum([x.likeability for x in reviews]))/len(reviews)
	
	@property
	def quality(self):
		reviews = self.professorreview_set.all()
		return float(sum([x.teaching_quality for x in reviews]))/len(reviews)

	def __unicode__(self):
		return u"{}".format(self.name)
	
class ProfessorReview(models.Model):
	professor = models.ForeignKey(Professor)
	author = models.ForeignKey(User)
	
	grading_toughness = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="1 being the easiest")
	likeability = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="1 being the least likable")
	teaching_quality = models.PositiveIntegerField(choices=RATING_CHOICES, help_text="1 being the worst")
	
	text = models.TextField()

	class Meta:
		unique_together = (('professor','author'))
		
	def __unicode__(self):
		return u"Review of {} by {}".format(self.professor, self.author)

class Department(models.Model):
	name = models.CharField(max_length=40)
	campus = models.CharField(max_length=2, choices=CAMPUS_CHOICES)
	code = models.CharField(max_length=4)
	
	class Meta:
		unique_together = (('name', 'campus'))
		
	def __unicode__(self):
		return u"{} ({})".format(self.name, self.campus)
	
class TimeSlot(models.Model):
	day = models.CharField(max_length=1, choices=DAY_CHOICES)
	start = models.TimeField()
	end = models.TimeField()
	
	class Meta:
		unique_together = (('start','end', 'day'))
		
	def __unicode__(self):
		return u"{} -- {}-{}".format(self.day, self.start, self.end)