from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, CreateUserForm, EditUserForm, PostForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts():
    return Post.objects.select_related(
        'author',
        'category',
        'location'
    ).filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def paginate_queryset(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    page_obj = paginate_queryset(request, get_published_posts())
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    posts = category.posts.select_related(
        'author',
        'category',
        'location'
    ).filter(
        is_published=True,
        pub_date__lte=timezone.now(),
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')

    page_obj = paginate_queryset(request, posts)
    return render(
        request,
        'blog/category.html',
        {
            'category': category,
            'page_obj': page_obj,
        }
    )


def profile(request, username):
    profile = get_object_or_404(User, username=username)

    if request.user == profile:
        posts = profile.posts.select_related(
            'author',
            'category',
            'location'
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
    else:
        posts = profile.posts.select_related(
            'author',
            'category',
            'location'
        ).filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

    page_obj = paginate_queryset(request, posts)
    return render(
        request,
        'blog/profile.html',
        {
            'profile': profile,
            'page_obj': page_obj,
        }
    )


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'category', 'location'),
        pk=post_id
    )

    if request.user != post.author and (
        not post.is_published
        or post.pub_date > timezone.now()
        or not post.category.is_published
    ):
        post = get_object_or_404(
            Post.objects.select_related('author', 'category', 'location').filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True,
            ),
            pk=post_id
        )

    comments = post.comments.select_related('author').all()
    form = CommentForm()

    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
            'comments': comments,
            'form': form,
        }
    )


def registration(request):
    form = CreateUserForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('login')
    return render(
        request,
        'registration/registration_form.html',
        {'form': form}
    )


@login_required
def edit_profile(request):
    form = EditUserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)

    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)

    form = PostForm(instance=post)

    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)

    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)

    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(
        request,
        'blog/comment.html',
        {
            'form': form,
            'comment': comment,
        }
    )


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)

    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    return render(
        request,
        'blog/comment.html',
        {
            'comment': comment,
        }
    )
